/**
 * sensor_buffer.cpp — Sliding Window Ring Buffer Implementation
 *
 * Ring buffer layout:
 *   _buf[_head] is the next slot to write.
 *   To export the window in chronological order, we reconstruct from _head
 *   around the ring.
 */
#include "sensor_buffer.h"
#include <string.h>

namespace SensorBuffer {

static Sample _buf[SENSOR_WINDOW_SIZE];
static int    _head  = 0;
static int    _count = 0;  // samples pushed so far (caps at SENSOR_WINDOW_SIZE)

void begin() {
    reset();
}

void push(const Sample& s) {
    _buf[_head] = s;
    _head = (_head + 1) % SENSOR_WINDOW_SIZE;
    if (_count < SENSOR_WINDOW_SIZE) _count++;
}

bool getWindow(Window& win) {
    if (_count < SENSOR_WINDOW_SIZE) {
        win.full = false;
        return false;
    }
    win.full = true;

    // Reconstruct chronological order from ring buffer
    // The oldest sample is at _head (the next slot to be overwritten)
    for (int step = 0; step < SENSOR_WINDOW_SIZE; step++) {
        int ring_idx = (_head + step) % SENSOR_WINDOW_SIZE;
        for (int ch = 0; ch < SENSOR_CHANNELS; ch++) {
            win.data[step * SENSOR_CHANNELS + ch] = _buf[ring_idx].channels[ch];
        }
    }
    return true;
}

void reset() {
    memset(_buf, 0, sizeof(_buf));
    _head  = 0;
    _count = 0;
}

} // namespace SensorBuffer
