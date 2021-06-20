#!/usr/bin/env python3
import math
from time import sleep
import numpy as np
import sounddevice as sd
from turn_signal_states import CaptureSequence

try:
    #audio  capture stuff:
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
            if (max_component > 0.12):
                df = dominant_frequency
                signal = None
                if (100 < df < 120): signal = "1*"
                if (120 < df < 143): signal = "2*"
                if (143 < df < 160): signal = "3*"
                if (160 < df < 179): signal = "4*"
                if (179 < df < 200): signal = "5*"
                print(signal)
                try:
                    sequence.signal_received(signal)
                except:
                    pass
        else:
            print('no input')

    #start sequence FSM
    sequence = CaptureSequence()
    sequence.start()

    with sd.InputStream(device=None, channels=1, callback=callback,
                        blocksize=int(samplerate * block_duration / 1000),
                        samplerate=samplerate):
        while True:
#            response = input()
            sleep(0.001)
            if sequence.state == 'sequence complete':
                break

except KeyboardInterrupt:
    print("exiting")
