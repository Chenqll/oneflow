import os
from collections import OrderedDict

import numpy as np
import oneflow as flow
import tensorflow as tf
import test_global_storage
from test_util import GenArgList

gpus = tf.config.experimental.list_physical_devices("GPU")
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)


def grouped_convolution2D(
    inputs, filters, padding, num_groups, strides=None, dilation_rate=None
):
    # Split input and outputs along their last dimension
    input_list = tf.split(inputs, num_groups, axis=-1)
    filter_list = tf.split(filters, num_groups, axis=-1)
    output_list = []

    # Perform a normal convolution on each split of the input and filters
    for conv_idx, (input_tensor, filter_tensor) in enumerate(
        zip(input_list, filter_list)
    ):
        output_list.append(
            tf.nn.conv2d(
                input_tensor,
                filter_tensor,
                padding="VALID",
                strides=[1, 1, 1, 1],
                data_format="NHWC",
            )
        )
    # Concatenate ouptputs along their last dimentsion
    outputs = tf.concat(output_list, axis=-1)
    return outputs


def compare_with_tensorflow(
    device_type, x_shape, filters, kernel_size, groups, padding="VALID", stride=1
):
    assert device_type in ["gpu", "cpu"]
    flow.clear_default_session()
    func_config = flow.FunctionConfig()
    func_config.default_data_type(flow.float)
    func_config.train.primary_lr(1e-4)
    func_config.train.model_update_conf(dict(naive_conf={}))

    @flow.global_function(func_config)
    def ConvJob():
        with flow.scope.placement(device_type, "0:0"):
            x = flow.get_variable(
                "x",
                shape=x_shape,
                dtype=flow.float,
                initializer=flow.random_uniform_initializer(minval=0, maxval=100),
                trainable=True,
            )
            weight_shape = (filters, int(x.shape[1] / groups), kernel_size, kernel_size)
            weight = flow.get_variable(
                "conv-weight",
                shape=weight_shape,
                dtype=flow.float,
                initializer=flow.random_uniform_initializer(minval=0, maxval=100),
            )
            loss = flow.nn.conv2d(
                x,
                weight,
                strides=[stride, stride],
                padding=padding,
                data_format="NCHW",
                dilations=[1, 1],
                groups=groups,
            )
            flow.losses.add_loss(loss)

            flow.watch(x, test_global_storage.Setter("x"))
            flow.watch_diff(x, test_global_storage.Setter("x_diff"))
            flow.watch(weight, test_global_storage.Setter("weight"))
            flow.watch_diff(weight, test_global_storage.Setter("weight_diff"))
            flow.watch(loss, test_global_storage.Setter("loss"))
            flow.watch_diff(loss, test_global_storage.Setter("loss_diff"))

            return loss

    # OneFlow
    check_point = flow.train.CheckPoint()
    check_point.init()
    of_out = ConvJob().get()
    # TensorFlow
    with tf.GradientTape(persistent=True) as tape:
        x = tf.Variable(test_global_storage.Get("x").transpose(0, 2, 3, 1))
        assert groups > 0
        assert x_shape[1] % groups == 0
        assert filters % groups == 0
        if groups == 1:
            weight = tf.Variable(
                test_global_storage.Get("weight").transpose(2, 3, 1, 0)
            )
            tf_out = tf.nn.conv2d(
                x,
                weight,
                strides=[1, stride, stride, 1],
                padding=padding,
                data_format="NHWC",
            )
        else:
            weight = tf.Variable(
                test_global_storage.Get("weight").transpose(2, 3, 1, 0)
            )
            tf_out = grouped_convolution2D(
                x, weight, padding=padding, num_groups=groups
            )

    loss_diff = test_global_storage.Get("loss_diff").transpose(0, 2, 3, 1)
    tf_x_diff = tape.gradient(tf_out, x, loss_diff)
    tf_weight_diff = tape.gradient(tf_out, weight, loss_diff)
    max_diff = np.max(
        np.absolute(of_out.numpy().transpose(0, 2, 3, 1) - tf_out.numpy())
    )
    assert np.allclose(
        of_out.numpy().transpose(0, 2, 3, 1), tf_out.numpy(), rtol=1e-5, atol=1e-5
    ), max_diff
    assert np.allclose(
        test_global_storage.Get("x_diff").transpose(0, 2, 3, 1),
        tf_x_diff.numpy(),
        rtol=1e-4,
        atol=1e-4,
    )
    assert np.allclose(
        test_global_storage.Get("weight_diff").transpose(2, 3, 1, 0),
        tf_weight_diff.numpy(),
        rtol=1e-5,
        atol=1e-5,
    )


def test_cpu1(test_case):
    return
    if os.getenv("ENABLE_USER_OP") == "False":
        return
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["cpu"]
    arg_dict["x_shape"] = [(10, 32, 226, 226)]
    arg_dict["filters"] = [128]
    arg_dict["kernel_size"] = [1]
    arg_dict["groups"] = [1]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_cpu2(test_case):
    return
    if os.getenv("ENABLE_USER_OP") == "False":
        return
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["cpu"]
    arg_dict["x_shape"] = [(10, 32, 226, 226)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [1]
    arg_dict["groups"] = [1]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_cpu3(test_case):
    return
    if os.getenv("ENABLE_USER_OP") == "False":
        return
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["cpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [5]
    arg_dict["groups"] = [1]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv1(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [3]
    arg_dict["groups"] = [1]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv2(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [3]
    arg_dict["groups"] = [4]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv3(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [3]
    arg_dict["groups"] = [8]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv4(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [3]
    arg_dict["groups"] = [32]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv5(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [1]
    arg_dict["groups"] = [8]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)


def test_conv6(test_case):
    arg_dict = OrderedDict()
    arg_dict["device_type"] = ["gpu"]
    arg_dict["x_shape"] = [(10, 32, 20, 20)]
    arg_dict["filters"] = [64]
    arg_dict["kernel_size"] = [1]
    arg_dict["groups"] = [32]
    for arg in GenArgList(arg_dict):
        compare_with_tensorflow(*arg)
