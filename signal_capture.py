#!/usr/bin/env python3
import math
from time import sleep
import numpy as np
import sounddevice as sd
from turn_signal_states import CaptureSequence

class AudioCapture():
    def __init__(self):
        self.last_max_component = 0
        self.gain = 10
        self.running = True
        bins = 156
        low = 320            #hz
        high = 1200          #hz
        delta_f = (high - low) / (bins)
        low_bin = math.floor(low / delta_f)
        self.block_duration = 50  #milliseconds
        try:
            self.samplerate = sd.query_devices(kind='input')['default_samplerate']
            self.fftsize = math.ceil(self.samplerate / delta_f)
        except KeyboardInterrupt:
            print("exiting")
            self.running = False

    def callback(self, indata, frames, time, status):
        if any(indata):
            magnitude = np.abs(np.fft.rfft(indata[:, 0], n=self.fftsize))
            magnitude *= self.gain / self.fftsize
            max_component = np.amax(magnitude)
            dominant_frequency = np.where(magnitude == np.amax(magnitude))[0][0]
            if (max_component > 0.12) and (max_component > self.last_max_component):
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
            self.last_max_component = max_component
        else:
            print('no input')

    def get_sequence(self):
            #start sequence FSM
            sequence = CaptureSequence()
            sequence.start()

            with sd.InputStream(device=None, channels=1, callback=self.callback,
                                blocksize=int(self.samplerate * self.block_duration / 1000),
                                samplerate=self.samplerate):
                while self.running:
                    sleep(0.001)
                    if sequence.state == 'sequence complete':
                        return sequence.turn_sequence

