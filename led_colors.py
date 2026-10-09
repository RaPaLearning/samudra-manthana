# The final RGB = ratio * brightness, so brightness 120 -> max channel 120.

# can also try ~brown #7F3F16 scaled (1.0, 0.5, 0.17)
SEA_COLOR_RATIO = (1.0, 0.23, 0) # (1.0, 0.7, 0.0) for white cloth
POISON_COLOR_RATIO = (1.0, 0.0, 1.0)  # purple

MAX_ALLOWED_BRIGHT = 200

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 170

SEA_COLOR_MAX = (int(BRIGHTNESS_MAX * SEA_COLOR_RATIO[0]),
                 int(BRIGHTNESS_MAX * SEA_COLOR_RATIO[1]),
                 int(BRIGHTNESS_MAX * SEA_COLOR_RATIO[2]))

SEA_COLOR_LOW = (int(BRIGHTNESS_MIN * SEA_COLOR_RATIO[0]),
                 int(BRIGHTNESS_MIN * SEA_COLOR_RATIO[1]),
                 int(BRIGHTNESS_MIN * SEA_COLOR_RATIO[2]))

POISON_COLOR_MAX = (int(BRIGHTNESS_MAX * POISON_COLOR_RATIO[0]),
                    int(BRIGHTNESS_MAX * POISON_COLOR_RATIO[1]),
                    int(BRIGHTNESS_MAX * POISON_COLOR_RATIO[2]))
