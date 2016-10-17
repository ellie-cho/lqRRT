"""
Constructs a planner that is good for boating around!

"""
from __future__ import division
import numpy as np
import numpy.linalg as npl

from params import *
import lqrrt

################################################# DYNAMICS

magic_rudder = 7000
focus = None

def dynamics(x, u, dt):
    """
    Returns next state given last state x, wrench u, and timestep dt.

    """
    # Rotation matrix (orientation, converts body to world)
    R = np.array([
                  [np.cos(x[2]), -np.sin(x[2]), 0],
                  [np.sin(x[2]),  np.cos(x[2]), 0],
                  [           0,             0, 1]
                ])

    # Construct drag coefficients based on our motion signs
    D = np.copy(D_neg)
    for i, v in enumerate(x[3:]):
        if v >= 0:
            D[i] = D_pos[i]

    # Heading controller for staring at some focus point
    if focus is not None:
        vec = focus[:2] - x[:2]
        ang = np.arctan2(vec[1], vec[0])
        c = np.cos(x[2])
        s = np.sin(x[2])
        cg = np.cos(ang)
        sg = np.sin(ang)
        u[2] = magic_rudder*np.arctan2(sg*c - cg*s, cg*c + sg*s)

    # Actuator saturation with even downscaling
    thrusts = invB.dot(u)
    ratios = thrust_max / np.clip(np.abs(thrusts), 1E-6, np.inf)
    if np.any(ratios < 1):
        u = B.dot(np.min(ratios) * thrusts)

    # M*vdot + D*v = u  and  pdot = R*v
    xdot = np.concatenate((R.dot(x[3:]), invM*(u - D*x[3:])))

    # First-order integrate
    xnext = x + xdot*dt

    return xnext

################################################# POLICY

kp = np.diag([150, 150, 2000])
kd = np.diag([120, 120, 0.01])
S = np.diag([1, 1, 1, 1, 1, 1])

def lqr(x, u):
    """
    Returns cost-to-go matrix S and policy matrix K given local state x and effort u.

    """
    R = np.array([
                  [np.cos(x[2]), -np.sin(x[2]), 0],
                  [np.sin(x[2]),  np.cos(x[2]), 0],
                  [           0,             0, 1]
                ])
    K = np.hstack((kp.dot(R.T), kd))
    return (S, K)

################################################# HEURISTICS

goal_buffer = [real_tol[0], real_tol[1], real_tol[2], np.inf, np.inf, real_tol[5]]
error_tol = np.copy(goal_buffer)

def gen_ss(seed, goal):
    """
    Returns a sample space given a seed state and goal state.

    """
    return [(min([seed[0], goal[0]]) - ss_buff, max([seed[0], goal[0]]) + ss_buff),
            (min([seed[1], goal[1]]) - ss_buff, max([seed[1], goal[1]]) + ss_buff),
            (-np.pi, np.pi),
            (-abs(velmax_neg[0]), velmax_pos[0]),
            (-abs(velmax_neg[1]), velmax_pos[1]),
            (-abs(velmax_neg[2]), velmax_pos[2])]

################################################# MAIN ATTRIBUTES

constraints = lqrrt.Constraints(nstates=nstates, ncontrols=ncontrols,
                                goal_buffer=goal_buffer, is_feasible=unset)

planner = lqrrt.Planner(dynamics, lqr, constraints,
                        horizon=horizon, dt=dt, FPR=FPR,
                        error_tol=error_tol, erf=unset,
                        min_time=basic_duration, max_time=basic_duration, max_nodes=max_nodes,
                        sys_time=unset, printing=False)
