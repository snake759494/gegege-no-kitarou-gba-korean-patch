"""Rasterize generated hand-painted source art to the original UI palette.

No font files or font rasterizers are used by this module.
"""
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LABELS = ['상태','체','기','공','방','운','돈','경험치','다음','키타로','사용','동료','장비','아이템 사용','아이템 장비']

def split_rows(path, expected):
    image = Image.open(path).convert('L')
    a = np.array(image)
    occupied = (a < 120).any(axis=1)
    runs=[]; start=None
    for y, on in enumerate(list(occupied)+[False]):
        if on and start is None: start=y
        if not on and start is not None:
            if y-start>8: runs.append((start,y))
            start=None
    if expected == 15:
        merged=[]
        for top,bottom in runs:
            if merged and top-merged[-1][1] <= 10:
                merged[-1]=(merged[-1][0],bottom)
            else: merged.append((top,bottom))
        runs=merged
    assert len(runs)==expected, (path,runs)
    result=[]
    for top,bottom in runs:
        row=a[top:bottom]; xs=np.where((row<120).any(axis=0))[0]
        result.append(image.crop((int(xs.min()),top,int(xs.max()+1),bottom)))
    return result

ART = dict(zip(LABELS,split_rows(ROOT/'assets/status_lettering_light.png',15)))
ENC = split_rows(ROOT/'assets/encyclopedia_lettering_source.png',4)

def paint(im, text, x, y, height=12, color=(32,24,24,255), center=False):
    source=ART[text]
    width=round(source.width*height/source.height)
    mask=np.array(source.resize((width,height),Image.Resampling.LANCZOS))<155
    if center:x-=width//2
    assert 0<=x and x+width<=im.width and y+height<=im.height,(text,x,y,width,height)
    for yy,xx in zip(*np.where(mask)):im.putpixel((x+int(xx),y+int(yy)),color)

def paint_box(im, text, box, height, color):
    """Center the actual visible ink on the original Japanese lettering box."""
    x0,y0,x1,y1=box
    source=ART[text]
    width=round(source.width*height/source.height)
    assert width<=x1-x0+4,(text,width,box)
    a=np.array(source.resize((width,height),Image.Resampling.LANCZOS))<155
    yy,xx=np.where(a)
    a=a[yy.min():yy.max()+1,xx.min():xx.max()+1]
    h,w=a.shape
    x=round((x0+x1-w)/2);y=round((y0+y1-h)/2)
    for yy,xx in zip(*np.where(a)):im.putpixel((x+int(xx),y+int(yy)),color)


def encyclopedia(im):
    # Keep the original left scroll's horizontal gradient instead of a flat fill.
    for y in range(30,126):
        for x in range(9,35):im.putpixel((x,y),im.getpixel((x,27)))
    for i,source in enumerate(ENC):
        mask=np.array(source.resize((19,20),Image.Resampling.LANCZOS))<155
        x=12;y=33+i*23
        for yy,xx in zip(*np.where(mask)):
            im.putpixel((x+int(xx)+1,y+int(yy)+1),(48,88,0,255))
        for yy,xx in zip(*np.where(mask)):
            im.putpixel((x+int(xx),y+int(yy)),(240,240,152,255))
