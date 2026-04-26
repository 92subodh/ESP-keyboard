#include <BleKeyboard.h>

BleKeyboard bleKeyboard("ESP32 Keyboard", "Espressif", 100);

void setup() {
  Serial.begin(115200);
  bleKeyboard.begin();
  Serial.println("BLE Keyboard ready. Waiting for connection...");
}

void loop() {
  if (bleKeyboard.isConnected()) {
    if (Serial.available()) {
      String token = Serial.readStringUntil('\n');
      token.trim();

      if (token.length() == 0) return;

      // ── Special key tokens ───────────────────────────────────
      if      (token == "[ENTER]") bleKeyboard.write(KEY_RETURN);
      else if (token == "[SPACE]") bleKeyboard.write(' ');        // ← THIS WAS MISSING
      else if (token == "[BACK]" ) bleKeyboard.write(KEY_BACKSPACE);
      else if (token == "[TAB]"  ) bleKeyboard.write(KEY_TAB);
      else if (token == "[DEL]"  ) bleKeyboard.write(KEY_DELETE);
      else if (token == "[ESC]"  ) bleKeyboard.write(KEY_ESC);
      else if (token == "[UP]"   ) bleKeyboard.write(KEY_UP_ARROW);
      else if (token == "[DOWN]" ) bleKeyboard.write(KEY_DOWN_ARROW);
      else if (token == "[LEFT]" ) bleKeyboard.write(KEY_LEFT_ARROW);
      else if (token == "[RIGHT]") bleKeyboard.write(KEY_RIGHT_ARROW);
      else if (token == "[HOME]" ) bleKeyboard.write(KEY_HOME);
      else if (token == "[END]"  ) bleKeyboard.write(KEY_END);
      else if (token == "[PGUP]" ) bleKeyboard.write(KEY_PAGE_UP);
      else if (token == "[PGDN]" ) bleKeyboard.write(KEY_PAGE_DOWN);

      // ── Single printable char ────────────────────────────────
      else if (token.length() == 1) {
        bleKeyboard.print(token[0]);
      }
      // unknown token → ignore silently
    }
  }
}