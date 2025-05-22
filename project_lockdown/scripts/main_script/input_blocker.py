#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from AppKit import NSApplication, NSApp, NSRunningApplication, NSApplicationActivationPolicyRegular
import signal
import sys
from Quartz.CoreGraphics import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CGDisplayHideCursor, CGDisplayShowCursor,
    kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventRightMouseDown,
    kCGEventOtherMouseDown, kCGEventLeftMouseUp, kCGEventRightMouseUp, kCGEventOtherMouseUp
)
from Quartz import CFRunLoopAddSource, CFRunLoopGetCurrent, CFRunLoopRun, kCFRunLoopDefaultMode

CGDisplayHideCursor(0)

def callback(proxy, type, event, refcon):
    return None

tap = CGEventTapCreate(
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    0,
    (1 << kCGEventMouseMoved) |
    (1 << kCGEventLeftMouseDown) |
    (1 << kCGEventRightMouseDown) |
    (1 << kCGEventOtherMouseDown) |
    (1 << kCGEventLeftMouseUp) |
    (1 << kCGEventRightMouseUp) |
    (1 << kCGEventOtherMouseUp),
    callback,
    None
)

def cleanup_and_exit(signum, frame):
    CGDisplayShowCursor(0)
    if tap:
        CGEventTapEnable(tap, False)
    print("\n🟢 Mouse input restored. Exiting.")
    sys.exit(0)

# Register signal handlers for clean exit
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

if tap:
    #print("🛑 Mouse input is now blocked. Press Ctrl+C to restore and exit.")
    loop_source = CFMachPortCreateRunLoopSource(None, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), loop_source, kCFRunLoopDefaultMode)
    CGEventTapEnable(tap, True)
    CFRunLoopRun()
else:
    print("❌ Не удалось создать ловушку событий мыши. Проверьте разрешения в Системных настройках > Безопасность и конфиденциальность > Универсальный доступ.")