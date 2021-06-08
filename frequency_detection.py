#!/usr/bin/env python3
import math
from time import sleep
import numpy as np
import sounddevice as sd


try:
    samplerate = sd.query_devices(kind='input')['default_samplerate']
    bins = 156
    low = 320            #hz
    high = 1200          #hz
    gain = 10
    delta_f = (high - low) / (bins)
    fftsize = math.ceil(samplerate / delta_f)
    low_bin = math.floor(low / delta_f)
    block_duration = 50  #milliseconds

    def callback(indata, frames, time, status):
        if any(indata):
            magnitude = np.abs(np.fft.rfft(indata[:, 0], n=fftsize))
            magnitude *= gain / fftsize
            max_component = np.amax(magnitude)
            dominant_frequency = np.where(magnitude == np.amax(magnitude))[0][0]
            if (max_component > 0.1):
                df = dominant_frequency
                if (100 < df < 120): print("1*")
                if (120 < df < 143): print("2*")
                if (143 < df < 160): print("3*")
                if (160 < df < 179): print("4*")
                if (179 < df < 200): print("5*")
        else:
            print('no input')

    with sd.InputStream(device=None, channels=1, callback=callback,
                        blocksize=int(samplerate * block_duration / 1000),
                        samplerate=samplerate):
        while True:
            response = input()
except KeyboardInterrupt:
    print("exiting")
