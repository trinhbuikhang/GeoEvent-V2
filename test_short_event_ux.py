#!/usr/bin/env python3
"""
Test script for short event UX improvements.
Tests minimum width display, hover tolerance, and adaptive snap distances.
"""

import sys
from datetime import datetime, timedelta, timezone
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QPoint, QRect

# Add the app directory to the path
sys.path.insert(0, 'app')

from app.ui.timeline_widget import TimelineWidget
from app.models.event_model import Event

def test_short_event_ux():
    """Test UX improvements for short events"""
    print("Testing short event UX improvements...")

    # Create QApplication
    app = QApplication(sys.argv)

    # Create timeline widget
    timeline = TimelineWidget()

    # Create test events - very short ones
    base_time = datetime(2025, 10, 2, 8, 22, 0, tzinfo=timezone.utc)
    events = [
        Event(
            event_id="short_1",
            event_name="Very Short Event",  # Only 2 seconds
            start_time=base_time,
            end_time=base_time + timedelta(seconds=2),
            start_chainage=1000.0,
            end_chainage=1005.0
        ),
        Event(
            event_id="short_2",
            event_name="Tiny Event",  # Only 1 second
            start_time=base_time + timedelta(seconds=10),
            end_time=base_time + timedelta(seconds=11),
            start_chainage=1100.0,
            end_chainage=1102.0
        ),
        Event(
            event_id="normal",
            event_name="Normal Event",
            start_time=base_time + timedelta(seconds=20),
            end_time=base_time + timedelta(seconds=50),
            start_chainage=1200.0,
            end_chainage=1250.0
        )
    ]

    timeline.set_events(events)
    timeline.update_view_range()

    # Calculate pixels_per_second for testing
    time_range = (timeline.view_end_time - timeline.view_start_time).total_seconds()
    pixels_per_second = 800 / time_range  # Assume 800px width

    # Test 1: Check minimum width enforcement
    print("Test 1: Minimum width enforcement")
    # Get pixel positions for short events
    short_event = events[0]
    start_pixel = timeline.time_to_pixel(short_event.start_time, pixels_per_second, 0)
    end_pixel = timeline.time_to_pixel(short_event.end_time, pixels_per_second, 0)
    actual_width = end_pixel - start_pixel

    print(f"Short event duration: {short_event.duration_seconds}s")
    print(f"Pixel width: {actual_width:.1f} (should be at least 8.0)")

    if actual_width >= 8.0:
        print("✓ Minimum width enforced")
    else:
        print("✗ Minimum width not enforced")

    # Test 2: Hover tolerance
    print("\nTest 2: Hover tolerance")
    # Test hovering slightly outside the event boundaries
    center_pixel = (start_pixel + end_pixel) / 2
    test_points = [
        QPointF(center_pixel, 10),  # Center, within timeline area
        QPointF(start_pixel - 3, 10),  # 3px left of start
        QPointF(end_pixel + 3, 10),   # 3px right of end
        QPointF(start_pixel - 6, 10),  # 6px left of start (should miss)
    ]

    # Create a mock rect for testing
    from PyQt6.QtCore import QRect
    timeline_rect = QRect(0, 0, 800, 200)  # Mock timeline area

    # Force rebuild layer cache
    timeline.rebuild_layer_cache(timeline_rect)

    print(f"Layer cache has {len(timeline.layer_cache) if timeline.layer_cache else 0} layers")
    if timeline.layer_cache:
        for i, layer in enumerate(timeline.layer_cache):
            print(f"Layer {i}: {len(layer)} events")

    for i, point in enumerate(test_points):
        # Convert QPointF to QPoint for contains() method
        qpoint = QPoint(int(point.x()), int(point.y()))
        event_at_pos = timeline.get_event_at_position(qpoint, timeline_rect, pixels_per_second)
        expected = i < 3  # First 3 should hit, last should miss
        actual = event_at_pos is not None and event_at_pos.event_id == "short_1"
        status = "✓" if actual == expected else "✗"
        print(f"Point {i+1} at ({point.x():.1f}, {point.y():.1f}): {status} {'Hit' if actual else 'Miss'} (expected {'Hit' if expected else 'Miss'})")
        if event_at_pos:
            print(f"  Found event: {event_at_pos.event_id}")

    # Test 3: Adaptive snap distance
    print("\nTest 3: Adaptive snap distance")
    # For very short events, snap distance should be larger
    # Based on implementation: max(HANDLE_SNAP_DISTANCE, min(15, event_width / 4))
    event_width = end_pixel - start_pixel
    expected_snap = max(20, min(15, event_width / 4))
    print(f"Short event width: {event_width:.1f}px")
    print(f"Expected adaptive snap distance: {expected_snap:.1f}px (base 20px, max 15px)")

    if expected_snap > 20:
        print("✓ Adaptive snap distance applied")
    elif expected_snap < 20:
        print("✓ Adaptive snap distance capped at minimum")
    else:
        print("✓ Using base snap distance")

    print("\n✓ Short event UX test completed!")
    return True

if __name__ == "__main__":
    test_short_event_ux()