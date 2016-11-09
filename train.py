#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

import os

import h5py

import brainstorm as bs
from brainstorm.data_iterators import Minibatches
from brainstorm.handlers import PyCudaHandler

from time import time

bs.global_rnd.set_seed(42)

# ---------------------------- Set up Iterators ----------------------------- #

data_dir = os.environ.get('BRAINSTORM_DATA_DIR', 'data')
data_file = os.path.join(data_dir, 'MNIST.hdf5')
ds = h5py.File(data_file, 'r')['normalized_split']
x_tr, y_tr = ds['training']['default'][:], ds['training']['targets'][:]
x_va, y_va = ds['validation']['default'][:], ds['validation']['targets'][:]

batch_size = 100
getter_tr = Minibatches(batch_size, default=x_tr, targets=y_tr)
getter_va = Minibatches(batch_size, default=x_va, targets=y_va)

# ----------------------------- Set up Network ------------------------------ #

inp, fc = bs.tools.get_in_out_layers('classification', (28, 28, 1), 10, projection_name='FC')
network = bs.Network.from_layer(
    inp >>
    bs.layers.Dropout(drop_prob=0.2) >>
    bs.layers.FullyConnected(1200, name='Hid1', activation='rel') >>
    bs.layers.Dropout(drop_prob=0.5) >>
    bs.layers.FullyConnected(1200, name='Hid2', activation='rel') >>
    bs.layers.Dropout(drop_prob=0.5) >>
    fc
)

# Uncomment next line to use GPU
network.set_handler(PyCudaHandler())
network.initialize(bs.initializers.Gaussian(0.01))
network.set_weight_modifiers({"FC": bs.value_modifiers.ConstrainL2Norm(1)})

# ----------------------------- Set up Trainer ------------------------------ #

trainer = bs.Trainer(bs.training.MomentumStepper(learning_rate=0.1, momentum=0.9))
trainer.add_hook(bs.hooks.ProgressBar())
scorers = [bs.scorers.Accuracy(out_name='Output.outputs.predictions')]
trainer.add_hook(bs.hooks.MonitorScores('valid_getter', scorers,
                                        name='validation'))
trainer.add_hook(bs.hooks.SaveBestNetwork('validation.Accuracy',
                                          filename='mnist_pi_best.hdf5',
                                          name='best weights',
                                          criterion='max'))
trainer.add_hook(bs.hooks.StopAfterEpoch(20))

# -------------------------------- Train ------------------------------------ #

start_time = time()
trainer.train(network, getter_tr, valid_getter=getter_va)
print("The training took %.4f seconds." % (time() - start_time))
print("Best validation accuracy:", max(trainer.logs["validation"]["Accuracy"]))
