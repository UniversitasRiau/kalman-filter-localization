# implementation of cubature kalman filter using CTRV model

# state matrix:                     2D x-y position, yaw, velocity, yaw rate and acceleration (6 x 1)
# input matrix:                     --None--
# measurement matrix:               2D noisy x-y position, yaw rate, acceleration, velocity from wheelspeed (5 x 1)

import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import sqrtm
import pandas as pd

# initalize global variables
amz = pd.read_csv('AMZ_data_non_resample_gps.csv')
dt_gps = 1/10                                                       # seconds
dt_imu = 1/200                                                       # seconds
dt_speed = 1/250                                                       # seconds
dt_wspeed = 1/100                                                       # seconds
# N = int(len(cfs['XX']))-1                                    # number of samples
N = 500

# prior mean
x_0 = np.array([[0.0],                                  # x position    [m]
                [0.0],                                  # y position    [m]
                [1e-6],                                 # yaw           [rad]
                [1e-6],                                 # velocity      [m/s]
                [1e-6],                                 # yaw rate      [rad/s]
                [1e-6]])                                # acceleration  [m/s^2]


# prior covariance
p_0 = np.array([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]])


# q matrix - process noise
q = np.array([[1e-6, 0.0, 0.0, 0.0, 0.0, 0.0],
              [0.0, 1e-6, 0.0, 0.0, 0.0, 0.0],
              [0.0, 0.0, 1e-8, 0.0, 0.0, 0.0],
              [0.0, 0.0, 0.0, 1e-8, 0.0, 0.0],
              [0.0, 0.0, 0.0, 0.0, 1e-4, 0.0],
              [0.0, 0.0, 0.0, 0.0, 0.0, 1e-4]])

# h matrix - measurement matrix
hx = np.array([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],      # x position    [m]
               [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],      # y position    [m]
               [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],      # velocity      [m/s]
               [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],      # yaw rate      [rad/s]
               [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]])     # acceleration  [m/s^2]

# r matrix - measurement noise covariance
r = np.array([[0.015, 0.0, 0.0, 0.0, 0.0],
              [0.0, 0.010, 0.0, 0.0, 0.0],
              [0.0, 0.0, 0.01, 0.0, 0.0],
              [0.0, 0.0, 0.0, 0.01, 0.0],
              [0.0, 0.0, 0.0, 0.0, 0.01]])**2


# main program
def main():
    # show_final = int(input('Display final result? (No/Yes = 0/1) : '))
    # show_animation = int(
    # input('Show animation of filter working? (No/Yes = 0/1) : '))
    # if show_animation == 1:
    # show_ellipse = int(
    # input('Display covariance ellipses in animation? (No/Yes = 0/1) : '))
    # else:
    # show_ellipse = 0
    show_final = 1
    show_animation = 0
    show_ellipse = 0
    x_est = x_0
    p_est = p_0
    # x_true = x_0
    # p_true = p_0
    # x_true_cat = np.array([x_0[0, 0], x_0[1, 0]])
    x_est_cat = np.array(
        [x_0[0, 0], x_0[1, 0], x_0[2, 0], x_0[3, 0], x_0[4, 0], x_0[5, 0]])
    z_cat = np.array([x_0[0, 0], x_0[1, 0], x_0[3, 0], x_0[4, 0], x_0[5, 0]])
    vel_cat = np.array([x_0[3, 0]])
    lat_vel_cat = np.array([x_0[3, 0]])
    for i in range(N):
        # x_true, p_true = extended_prediction(x_true, p_true)
        z, vel = gen_measurement(i)
        if i == (N - 1) and show_final == 1:
            show_final_flag = 1
        else:
            show_final_flag = 0
        # x_true_cat = np.vstack((x_true_cat, np.transpose(x_true[0:2])))
        z_cat = np.vstack((z_cat, np.transpose(z[0:5])))
        # vel_cat = np.vstack((vel_cat, vel * np.sin(x_est[2])))
        vel_cat = np.vstack((vel_cat, vel))
        lat_vel_cat = np.vstack((lat_vel_cat, x_est[3] * np.cos(x_est[2])))
        x_est_cat = np.vstack((x_est_cat, np.transpose(x_est[0:6])))
        postpross(i, x_est, p_est, x_est_cat, z,
                  z_cat, vel_cat, lat_vel_cat, show_animation, show_ellipse, show_final_flag)
        x_est, p_est = cubature_kalman_filter(x_est, p_est, z)
    print('CKF Over')


# cubature kalman filter
def cubature_kalman_filter(x_est, p_est, z):
    x_pred, p_pred = cubature_prediction(x_est, p_est)
    # return x_pred.astype(float), p_pred.astype(float)
    x_upd, p_upd = cubature_update(x_pred, p_pred, z)
    return x_upd.astype(float), p_upd.astype(float)


# CTRV motion model f matrix
def f(x):
    x[0] = x[0] + (x[3]/x[4]) * (np.sin(x[4] * dt + x[2]) - np.sin(x[2]))
    x[1] = x[1] + (x[3]/x[4]) * (- np.cos(x[4] * dt + x[2]) + np.cos(x[2]))
    x[2] = x[2] + x[4] * dt
    x[3] = x[3] + x[5] * dt
    x[4] = x[4]
    x[5] = x[5]
    x.reshape((6, 1))
    return x.astype(float)


# CTRV measurement model h matrix
def h(x):
    x = hx @ x
    x.reshape((5, 1))
    return x


# generate sigma points
def sigma(x, p):
    n = np.shape(x)[0]
    SP = np.zeros((n, 2*n))
    W = np.zeros((1, 2*n))
    for i in range(n):
        SD = sqrtm(p)
        SP[:, i] = (x + (math.sqrt(n) * SD[:, i]).reshape((n, 1))).flatten()
        SP[:, i+n] = (x - (math.sqrt(n) * SD[:, i]).reshape((n, 1))).flatten()
        W[:, i] = 1/(2*n)
        W[:, i+n] = W[:, i]
    return SP.astype(float), W.astype(float)


# cubature kalman filter nonlinear prediction step
def cubature_prediction(x_pred, p_pred):
    n = np.shape(x_pred)[0]
    [SP, W] = sigma(x_pred, p_pred)
    x_pred = np.zeros((n, 1))
    p_pred = q
    for i in range(2*n):
        x_pred = x_pred + (f(SP[:, i]).reshape((n, 1)) * W[0, i])
    for i in range(2*n):
        p_step = (f(SP[:, i]).reshape((n, 1)) - x_pred)
        p_pred = p_pred + (p_step @ np.transpose(p_step) * W[0, i])
    return x_pred.astype(float), p_pred.astype(float)


# cubature kalman filter nonlinear update step
def cubature_update(x_pred, p_pred, z):
    n = np.shape(x_pred)[0]
    m = np.shape(z)[0]
    [SP, W] = sigma(x_pred, p_pred)
    y_k = np.zeros((m, 1))
    P_xy = np.zeros((n, m))
    s = r
    for i in range(2*n):
        y_k = y_k + (h(SP[:, i]).reshape((m, 1)) * W[0, i])
    for i in range(2*n):
        p_step = (h(SP[:, i]).reshape((m, 1)) - y_k)
        P_xy = P_xy + ((SP[:, i]).reshape((n, 1)) -
                       x_pred) @ np.transpose(p_step) * W[0, i]
        s = s + p_step @ np.transpose(p_step) * W[0, i]
    x_pred = x_pred + P_xy @ np.linalg.pinv(s) @ (z - y_k)
    p_pred = p_pred - P_xy @ np.linalg.pinv(s) @ np.transpose(P_xy)
    return x_pred, p_pred


# cubature kalman filter linear update step
def linear_update(x_pred, p_pred, z):
    s = h @ p_pred @ np.transpose(h) + r
    k = p_pred @ np.transpose(h) @ np.linalg.pinv(s)
    v = z - h @ x_pred

    x_upd = x_pred + k @ v
    p_upd = p_pred - k @ s @ np.transpose(k)
    return x_upd.astype(float), p_upd.astype(float)


# generate ground truth measurement vector gz, noisy measurement vector z
def gen_measurement(i):
    x = float(cfs['XX'][i+1])
    y = float(cfs['YY'][i+1])
    vel = float(cfs['tv_velocity'][i+1])
    v = float(cfs['GPSVel'][i+1])
    wZsens = float(cfs['yawRate'][i+1])
    a_x = float(cfs['ax'][i+1]) - 1.0
    a_y = float(cfs['ay'][i+1])
    acc = np.sqrt(a_x**2 + a_y**2)
    gz = np.array([[x], [y], [v], [wZsens], [a_x]])
    # z = gz + z_noise @ np.random.randn(4, 1)
    return gz.astype(float), float(vel)


# postprocessing
def plot_animation(i, x_est_cat, z):
    if i == 0:
        plt.plot(z[0], z[1], 'g+')
        plt.plot(x_est_cat[0], x_est_cat[1], '.b')
    else:
        plt.plot(z[0], z[1], 'g+')
        plt.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b')
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


def plot_final(x_est_cat, z_cat):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b', label='Estimated Position')
    f.plot(z_cat[0:, 0], z_cat[0:, 1], '+g', label='Noisy Measurements')
    f.set_xlabel('x [m]')
    f.set_ylabel('y [m]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def plot_final_2(x_est_cat, z_cat, i):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 2] * 180/np.pi, 'b', label='Estimated Yaw')
    f.set_xlabel('Sample')
    f.set_ylabel('Yaw [degrees]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def plot_final_3(x_est_cat, z_cat, vel_cat, i):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    # f.plot(est_vel_cat[0:], 'b', label='Estimated Velocity')
    f.plot(x_est_cat[0:, 3], 'b', label='Estimated Longitudinal Velocity')
    f.plot(vel_cat, '+g', label='Noisy Measurements')
    f.set_xlabel('Sample')
    f.set_ylabel('Velocity [m/s]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def plot_final_4(x_est_cat, z_cat, i):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 4], 'b', label='Estimated Yaw Rate')
    f.plot(z_cat[0:, 2], '+g', label='Noisy Measurements')
    f.set_xlabel('Sample')
    f.set_ylabel('Yaw Rate [rad/s]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def plot_final_5(x_est_cat, z_cat, i):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 5], 'b', label='Estimated Acceleration')
    f.plot(z_cat[0:, 3], '+g', label='Noisy Measurements')
    f.set_xlabel('Sample')
    f.set_ylabel('Acceleration [m/s^2]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def plot_final_6(x_est, z_cat, lat_vel_cat, i):
    fig = plt.figure()
    f = fig.add_subplot(111)
    # f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(lat_vel_cat[0:], 'b', label='Estimated Lateral Velocity')
    # f.plot(z_cat[0:, 3], '+g', label='Noisy Measurements')
    f.set_xlabel('Sample')
    f.set_ylabel('Velocity [m/s]')
    f.set_title('Cubature Kalman Filter - CTRA Model')
    f.legend(loc='upper right', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


def postpross(i, x_est, p_est, x_est_cat, z, z_cat, vel_cat, lat_vel_cat, show_animation, show_ellipse, show_final_flag):
    if show_animation == 1:
        plot_animation(i, x_est_cat, z)
        if show_ellipse == 1:
            plot_ellipse(x_est[0:2], p_est)
    if show_final_flag == 1:
        plot_final_3(x_est_cat, z_cat, vel_cat, i)
        # plot_final_5(x_est_cat, z_cat, i)
        # plot_final_6(x_est, z_cat, lat_vel_cat, i)
        # plot_final(x_est_cat, z_cat)


main()
