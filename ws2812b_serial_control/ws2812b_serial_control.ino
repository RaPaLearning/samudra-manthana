/*
  WS2812B Serial Control
  -----------------------
  Listens on the serial port for commands of the form:

      >startLed endLed R G B<

  Example:
      >2 20 40 50 60<

  This sets LEDs at index 2 through 20 (inclusive) to RGB(40, 50, 60).

  Wiring:
    - WS2812B data pin -> Arduino D6 (use a ~330-470 ohm resistor in series
      if you have one handy; not strictly required for short runs)
    - WS2812B 5V -> external 5V supply (don't power long strips from the
      Uno's 5V pin)
    - WS2812B GND -> shared GND with the Arduino AND the external supply

  Library required: Adafruit NeoPixel
    Arduino IDE -> Sketch -> Include Library -> Manage Libraries ->
    search "Adafruit NeoPixel" -> Install
*/

#include <Adafruit_NeoPixel.h>

#define LED_PIN     6      // Data pin connected to D6
#define NUM_LEDS    250     // Change this to match your actual strip length
#define BAUD_RATE   9600

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Buffer for accumulating one command between '>' and '<'
const uint8_t CMD_BUF_SIZE = 64;
char cmdBuf[CMD_BUF_SIZE];
uint8_t cmdIndex = 0;
bool receiving = false;

void setup() {
  Serial.begin(BAUD_RATE);
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

  Serial.println(F("WS2812B control 1 ready."));
  Serial.println(F("Send commands like: >2 20 40 50 60<"));
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '>') {
      // Start of a new command - reset buffer
      cmdIndex = 0;
      receiving = true;
    }
    else if (c == '<') {
      // End of command - process it if we were receiving
      if (receiving) {
        cmdBuf[cmdIndex] = '\0'; // null-terminate
        processCommand(cmdBuf);
      }
      receiving = false;
      cmdIndex = 0;
    }
    else if (receiving) {
      // Accumulate characters between '>' and '<'
      if (cmdIndex < CMD_BUF_SIZE - 1) {
        cmdBuf[cmdIndex++] = c;
      }
      // If buffer would overflow, silently drop extra chars until '<' or '>'
    }
    // Any character outside a '>' ... '<' block is ignored
  }
}

void processCommand(char* cmd) {
  int startLed, endLed, r, g, b;

  // Expected format: "startLed endLed R G B"
  int parsed = sscanf(cmd, "%d %d %d %d %d", &startLed, &endLed, &r, &g, &b);

  if (parsed != 5) {
    Serial.print(F("Error: could not parse command: "));
    Serial.println(cmd);
    return;
  }

  // Clamp RGB values to valid byte range
  r = constrain(r, 0, 255);
  g = constrain(g, 0, 255);
  b = constrain(b, 0, 255);

  // Allow start/end in either order
  if (startLed > endLed) {
    int tmp = startLed;
    startLed = endLed;
    endLed = tmp;
  }

  // Validate LED index range
  if (startLed < 0 || endLed >= NUM_LEDS) {
    Serial.print(F("Error: LED index out of range (0-"));
    Serial.print(NUM_LEDS - 1);
    Serial.print(F("): "));
    Serial.println(cmd);
    return;
  }

  for (int i = startLed; i <= endLed; i++) {
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
  strip.show();

  Serial.print(F("OK: set LEDs "));
  Serial.print(startLed);
  Serial.print(F(" to "));
  Serial.print(endLed);
  Serial.print(F(" -> R="));
  Serial.print(r);
  Serial.print(F(" G="));
  Serial.print(g);
  Serial.print(F(" B="));
  Serial.println(b);
}
