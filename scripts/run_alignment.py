"""Run the same alignment parameters on every plate; save images and numeric results.
Usage: python scripts/run_alignment.py --input ../data --output part-two/results
"""
from pathlib import Path
import argparse, csv, json, time
from PIL import Image
import numpy as np
from alignment import split_plate, search, pyramid_align, low_resolution, compose


def save_web(image,path,max_side=1100):
    image=image.copy();image.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
    image.save(path,quality=91,optimize=True)


def run(input_dir, output):
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    sources=sorted(p for p in input_dir.iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.png','.tif','.tiff'} and not p.name.startswith('._'))
    for source in sources:
        start=time.perf_counter();folder=output/source.stem;folder.mkdir(exist_ok=True)
        with Image.open(source) as plate:
            source_size=list(plate.size);channels=split_plate(plate)
            save_web(plate.convert('RGB'),folder/'plate.jpg',1200)
        low=low_resolution(channels)
        t=time.perf_counter();g_low,sg=search(low[0],low[1]);r_low,sr=search(low[0],low[2]);single_seconds=time.perf_counter()-t
        im,_=compose(low);save_web(im,folder/'single-before.jpg')
        im,_=compose(low,g_low,r_low);save_web(im,folder/'single.jpg')
        t=time.perf_counter();g,gt=pyramid_align(channels[0],channels[1]);r,rt=pyramid_align(channels[0],channels[2]);pyramid_seconds=time.perf_counter()-t
        im,bounds=compose(channels,g,r)
        im.save(folder/'aligned-full.jpg',quality=94,optimize=True)
        save_web(im,folder/'aligned.jpg')
        # EXACT same B-coordinate canvas for before/after: slider never compares different crops.
        before,_=compose(channels,bounds=bounds);save_web(before,folder/'before.jpg')
        uncropped,_=compose(channels);save_web(uncropped,folder/'unaligned-full-view.jpg')
        for label,ch in zip(('b','g','r'),channels):
            save_web(Image.fromarray(np.round(ch*255).astype(np.uint8)),folder/f'channel-{label}.jpg',600)
        rec={'id':source.stem,'source':source.name,'source_size':source_size,'channel_size':[channels[0].shape[1],channels[0].shape[0]],'discarded_rows':source_size[1]%3,'single_size':[low[0].shape[1],low[0].shape[0]],'single':{'green':list(g_low),'red':list(r_low),'green_ncc':round(sg,6),'red_ncc':round(sr,6),'seconds':round(single_seconds,3)},'pyramid':{'green':list(g),'red':list(r),'seconds':round(pyramid_seconds,3),'green_trace':gt,'red_trace':rt},'crop_bounds':list(bounds),'output_size':list(im.size),'total_seconds':round(time.perf_counter()-start,3)}
        records.append(rec)
        (output/'results.json').write_text(json.dumps({'parameters':{'metric':'zero-mean NCC','border_fraction':0.1,'single_max_side':400,'single_radius':15,'coarse_max_side':192,'coarse_radius':15,'refine_radius':2,'pyramid_blur_sigma':1.0},'images':records},indent=2),encoding='utf-8')
        print(f'{source.name}: G={g} R={r} | single {single_seconds:.2f}s / pyramid {pyramid_seconds:.2f}s',flush=True)
    with (output/'offsets.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['image','method','width','height','G_dx','G_dy','R_dx','R_dy','seconds'])
        for r in records:
            for method,size in [('single',r['single_size']),('pyramid',r['channel_size'])]:
                result=r[method];writer.writerow([r['source'],method,*size,*result['green'],*result['red'],result['seconds']])
    print(f'Finished {len(records)} plates.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=Path('../data'));parser.add_argument('--output',type=Path,default=Path('part-two/results'));args=parser.parse_args();run(args.input,args.output)
