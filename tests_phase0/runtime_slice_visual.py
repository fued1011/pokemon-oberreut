#!/usr/bin/env python3
"""Walk to repeatable slice cameras using real keys, never RAM writes."""
import datetime
import json
import tempfile
from collections import deque
from pathlib import Path
import struct

from mgba._pylib import lib
from mgba.gba import GBA
from runtime_mgba import ROOT, open_game, frames, press, location


def route(start, goal):
    cells=struct.unpack('<4096H',(ROOT/'data/layouts/Oberreut/map.bin').read_bytes())
    pending=deque([start]); previous={start:None}
    while pending:
        here=pending.popleft()
        if here==goal:break
        for dx,dy,key in ((1,0,'RIGHT'),(-1,0,'LEFT'),(0,1,'DOWN'),(0,-1,'UP')):
            point=(here[0]+dx,here[1]+dy)
            x,y=point
            if 0<=x<64 and 0<=y<64 and not cells[y*64+x]&0xc00 and point not in previous:
                previous[point]=(here,key);pending.append(point)
    assert goal in previous, ('Unreachable camera',goal)
    path=[];point=goal
    while previous[point]:
        prior,key=previous[point];path.append((point,key));point=prior
    return path[::-1]


def main():
    with tempfile.TemporaryDirectory(prefix='oberreut-slice-') as folder:
        gba,framebuffer=open_game(Path(folder)/'isolated.sav')
        gba._core.rtc.override=lib.RTC_FIXED
        gba._core.rtc.value=int(datetime.datetime(2026,10,31,12).astimezone().timestamp()*1000)
        gba.reset();frames(gba,400);press(gba,'START',90)
        for _ in range(250):
            press(gba,'A')
            if location(gba)==[0,57,30,28]:break
        else:raise AssertionError('New Game did not reach Oberreut')
        frames(gba,900)
        for name,goal in (('plaza',(30,28)),('facade',(30,17)),('tram',(44,24)),('south',(38,36))):
            for point,key in route(tuple(location(gba)[2:]),goal):
                gba.set_keys(getattr(GBA,'KEY_'+key))
                for _ in range(80):
                    gba.run_frame()
                    if tuple(location(gba)[2:])==point:break
                else:raise AssertionError((name,point,location(gba)))
                gba.set_keys();frames(gba,20)
                assert location(gba)==[0,57,*point],location(gba)
            frames(gba,60)
            output=ROOT/f'logs/slice-{name}-day.png'
            framebuffer.to_pil().convert('RGB').save(output)
            print(json.dumps({'camera':name,'location':location(gba),'framebuffer':str(output)}),flush=True)


if __name__=='__main__':main()
