# implementation of extended kalman filter using CT model

# state matrix:                     2D x-y position, velocity, yaw and yaw rate (5 x 1)
# input matrix:                     --None--
# measurement matrix:               2D noisy x-y position measured directly and yaw rate (3 x 1)

import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import sqrtm
import pandas as pd

# initalize global variables
cfs = pd.read_csv('cfs_data_fsn17.csv')
dt = 0.1                                               # seconds
# N = int(len(cfs['XX']))-1                               # number of samples
N = 300

z_noise = np.array([[1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0]])                   # measurement noise


# prior mean
x_0 = np.array([[0.0],                                  # x position    [m]
                [0.0],                                  # y position    [m]
                [0.0000001],                            # yaw           [rad]
                [0.0000001],                            # velocity      [m/s]
                [0.0000001]])                           # yaw rate      [rad/s]


# prior covariance
p_0 = np.array([[1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0]])


# q matrix - process noise
q = np.array([[1e-6, 0.0,       0.0,                0.0, 0.0],
              [0.0, 1e-6,       0.0,                0.0, 0.0],
              [0.0, 0.0,        1e-6,               0.0, 0.0],
              [0.0, 0.0,        0.0,                1e-6, 0.0],
              [0.0, 0.0,        0.0,                0.0, 1e-6]])

# h matrix - measurement matrix
hx = np.array([[1.0, 0.0, 0.0, 0.0, 0.0],
               [0.0, 1.0, 0.0, 0.0, 0.0],
               [0.0, 0.0, 0.0, 0.0, 1.0]])

# r matrix - measurement noise covariance
r = np.array([[0.015, 0.0, 0.0],
              [0.0, 0.010, 0.0],
              [0.0, 0.0, 0.01]])**2

# main program
def main():
    show_final = int(input('Display final result? (No/Yes = 0/1) : '))
    show_animation = int(
        input('Show animation of filter working? (No/Yes = 0/1) : '))
    if show_animation == 1:
        show_ellipse = int(
            input('Display covariance ellipses in animation? (No/Yes = 0/1) : '))
    else:
        show_ellipse = 0
    x_est = x_0
    p_est = p_0
    x_true = x_0
    p_true = p_0
    x_true_cat = np.array([x_0[0, 0], x_0[1, 0]])
    x_est_cat = np.array([x_0[0, 0], x_0[1, 0]])
    z_cat = np.array([x_0[0, 0], x_0[1, 0]])
    for i in range(N):
        x_true, p_true = extended_prediction(x_true, p_true)
        gz = gen_measurement(x_true, i)
        if i == (N - 1) and show_final == 1:
            show_final_flag = 1
        else:
            show_final_flag = 0
        postpross(i, x_true, x_true_cat, x_est, p_est, x_est_cat, gz,
                  z_cat, show_animation, show_ellipse, show_final_flag)
        x_est, p_est = extended_kalman_filter(x_est, p_est, gz)
        x_true_cat = np.vstack((x_true_cat, np.transpose(x_true[0:2])))
        z_cat = np.vstack((z_cat, np.transpose(gz[0:2])))
        x_est_cat = np.vstack((x_est_cat, np.transpose(x_est[0:2])))
    print('EKF Over')


# generate ground truth measurement vector gz, noisy measurement vector z
def gen_measurement(x_true, i):
    x = float(cfs['XX'][i+1])
    y = float(cfs['YY'][i+1])
    wZsens = float(cfs['yawRate'][i+1])
    gz = np.array([[x], [y], [wZsens]])
    z = gz + z_noise @ np.random.randn(3, 1)
    return gz


# extended kalman filter
def extended_kalman_filter(x_est, p_est, z):
    x_pred, p_pred = extended_prediction(x_est, p_est)
    # return x_pred, p_pred
    x_upd, p_upd = linear_update(x_pred, p_pred, z)
    return x_upd, p_upd


# extended kalman filter nonlinear prediction step
def extended_prediction(x, p):

    # f(x)
    x[0] = x[0] + dt * (x[3]) * np.cos(x[4])
    x[1] = x[1] + dt * (x[3]) * np.sin(x[4])
    x[2] = x[2]
    x[3] = x[3] + x[4] * dt
    x[4] = x[4]
    x_pred = x
    
    jF = np.array([[1, 0, dt * np.cos(x[4]), -dt * x[3] * np.sin(x[4]), 0],
                   [0, 1, dt * np.sin(x[4]), dt * x[3] * np.cos(x[4]),  0],
                   [0, 0, 1,             0,                             0],
                   [0, 0, 0,             1,                             dt],
                   [0, 0, 0,             0,                             1]])
    
    p_pred = jF @ p @ np.transpose(jF) + q
    return x_pred.astype(float), p_pred.astype(float)


# extended kalman filter linear update step
def linear_update(x_pred, p_pred, z):
    s = hx @ p_pred @ np.transpose(hx) + r
    k = p_pred @ np.transpose(hx) @ np.linalg.pinv(s)
    v = z - hx @ x_pred

    x_upd = x_pred + k @ v
    p_upd = p_pred - k @ s @ np.transpose(k)
    return x_upd.astype(float), p_upd.astype(float)


# postprocessing
def plot_animation(i, x_true_cat, x_est_cat, z):
    if i == 0:
        plt.plot(x_true_cat[0], x_true_cat[1], '.r')
        plt.plot(x_est_cat[0], x_est_cat[1], '.b')
    else:
        plt.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r')
        plt.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b')
    plt.plot(z[0], z[1], '+g')
    plt.grid(True)
    plt.pause(0.001)


def plot_ellipse(x_est, p_est):
    phi = np.linspace(0, 2 * math.pi, 100)
    p_ellipse = np.array(
        [[p_est[0, 0], p_est[0, 1]], [p_est[1, 0], p_est[1, 1]]])
    x0 = 3 * sqrtm(p_ellipse)
    xy_1 = np.array([])
    xy_2 = np.array([])
    for i in range(100):
        arr = np.array([[math.sin(phi[i])], [math.cos(phi[i])]])
        arr = x0 @ arr
        xy_1 = np.hstack([xy_1, arr[0]])
        xy_2 = np.hstack([xy_2, arr[1]])
    plt.plot(xy_1 + x_est[0], xy_2 + x_est[1], 'r')
    plt.pause(0.00001)


def plot_final(x_true_cat, x_est_cat, z_cat):
    fig = plt.figure()
    f = fig.add_subplot(111)
    f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b', label='Estimated Position')
    f.plot(z_cat[0:, 0], z_cat[0:, 1], '+g', label='Noisy Measurements')
    f.set_xlabel('x [m]')
    f.set_ylabel('y [m]')
    f.set_title('Extended Kalman Filter - CT Model')
    f.legend(loc='upper left', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def postpross(i, x_true, x_true_cat, x_est, p_est, x_est_cat, z, z_cat, show_animation, show_ellipse, show_final_flag):
    if show_animation == 1:
        plot_animation(i, x_true_cat, x_est_cat, z)
        if show_ellipse == 1:
            plot_ellipse(x_est[0:2], p_est)
    if show_final_flag == 1:
        plot_final(x_true_cat, x_est_cat, z_cat)


main()
