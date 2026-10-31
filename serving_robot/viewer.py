"""Optional native MuJoCo viewer. Use ../.venv/bin/mjpython viewer.py."""
import argparse,time
import mujoco.viewer
from sim import Simulation
p=argparse.ArgumentParser();p.add_argument('--goal',choices=['table1','table2','table3','kitchen'],default='table2');a=p.parse_args()
sim=Simulation();sim.go(a.goal)
with mujoco.viewer.launch_passive(sim.model,sim.data) as viewer:
    viewer.cam.lookat[:]=[3,3,0];viewer.cam.distance=9;viewer.cam.elevation=-70
    while viewer.is_running():
        start=time.monotonic();sim.step();viewer.sync();time.sleep(max(0,.01-(time.monotonic()-start)))
