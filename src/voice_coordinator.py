#!/usr/bin/env python3
"""
DisasterShield Voice Coordinator
Professional emergency announcements and text-to-speech coordination
"""

import sys
import time
import threading
import queue
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import subprocess
import logging
import itertools
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Priority(Enum):
    """Voice announcement priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class VoiceEngine(Enum):
    """Available text-to-speech engines"""
    SYSTEM_TTS = "system"
    PYTTSX3 = "pyttsx3"
    GTTS = "gtts"
    ESPEAK = "espeak"


@dataclass
class VoiceAnnouncement:
    """Voice announcement data structure"""
    message: str
    priority: Priority
    timestamp: datetime
    category: str
    engine: VoiceEngine = VoiceEngine.SYSTEM_TTS
    voice_speed: float = 0.9
    voice_pitch: float = 1.0
    voice_volume: float = 0.8


class VoiceCoordinator:
    """
    Professional voice coordination system for emergency operations
    Handles text-to-speech, priority queuing, and multi-platform support
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.voice_enabled = True
        self.announcement_queue: "queue.PriorityQueue[Tuple[int,int,VoiceAnnouncement]]" = queue.PriorityQueue()
        self.announcement_history: List[VoiceAnnouncement] = []
        self.current_engine = VoiceEngine.SYSTEM_TTS
        self.is_speaking = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        self._seq = itertools.count()  # tie-breaker for PriorityQueue

        # Voice settings
        self.voice_settings = {
            'rate': 160,     # Words per minute
            'volume': 0.8,
            'voice_id': None  # Set to e.g. "Alex" on macOS if desired
        }

        # Emergency message templates
        self.message_templates = {
            'system_start': "DisasterShield emergency response system now online",
            'threat_detected': "Emergency threat detected. Initiating autonomous response protocols",
            'earthquake': "Earthquake event detected. Magnitude {magnitude}. Autonomous coordination active",
            'hurricane': "Hurricane threat detected. Category {category}. Emergency protocols initiated",
            'wildfire': "Wildfire emergency detected. Evacuation coordination in progress",
            'response_complete': "Autonomous response complete. {lives} lives protected",
            'system_ready': "All systems operational. Ready for emergency response",
            'coordination_active': "Multi-agency coordination active. {agencies} agencies coordinated",
            'population_alert': "{count} citizens reached via emergency alert system",
            'evacuation_active': "Evacuation routes active. {routes} primary routes operational",
            'resource_deployed': "{resources} emergency resources deployed to affected areas",
            # IBM watsonx-specific announcements
            'watsonx_startup': "IBM watsonx ecosystem initializing. Granite models loading.",
            'multi_model_coordination': "Multiple Granite models coordinating for optimal response",
            'orchestrate_workflow': "watsonx Orchestrate managing {workflow_count} concurrent workflows",
            'guardian_validation': "Granite Guardian validating safety of all emergency decisions",
            'assistant_ready': "watsonx Assistant ready for natural language emergency commands",
            'ecosystem_showcase': "Demonstrating complete IBM watsonx artificial intelligence ecosystem",
        }

        # Initialize TTS engine
        self._initialize_tts_engine()

        # Start worker thread
        self._start_worker_thread()

    def _initialize_tts_engine(self):
        """Initialize the best available TTS engine for the platform"""
        engines_to_test = [
            (VoiceEngine.SYSTEM_TTS, self._test_system_tts),
            (VoiceEngine.PYTTSX3, self._test_pyttsx3),
            (VoiceEngine.ESPEAK, self._test_espeak),
        ]

        for engine, test_func in engines_to_test:
            if test_func():
                self.current_engine = engine
                logger.info(f"Voice engine initialized: {engine.value}")
                return

        logger.warning("No TTS engine available. Voice announcements disabled.")
        self.voice_enabled = False

    def _test_system_tts(self) -> bool:
        """Test system TTS availability without speaking."""
        try:
            if sys.platform == "darwin":  # macOS
                return shutil.which("say") is not None
            elif sys.platform == "win32":  # Windows (use pyttsx3 for SAPI)
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.stop()
                    return True
                except Exception:
                    return False
            elif sys.platform.startswith("linux"):  # Linux uses espeak
                return shutil.which("espeak") is not None
        except Exception:
            return False
        return False

    def _test_pyttsx3(self) -> bool:
        """Test pyttsx3 availability"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.stop()
            return True
        except Exception:
            return False

    def _test_espeak(self) -> bool:
        """Test espeak availability"""
        try:
            return shutil.which("espeak") is not None
        except Exception:
            return False

    def _start_worker_thread(self):
        """Start the worker thread for processing announcements"""
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=self._process_announcements, daemon=True
        )
        self.worker_thread.start()
        logger.info("Voice coordinator worker thread started")

    def _process_announcements(self):
        """Worker thread to process announcement queue"""
        while not self.stop_event.is_set():
            try:
                # Get next announcement (blocks until available)
                priority_value, _, announcement = self.announcement_queue.get(timeout=1.0)

                if self.enabled and self.voice_enabled:
                    self._speak_announcement(announcement)

                # Mark task as done
                self.announcement_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing announcement: {e}")

    def _speak_announcement(self, announcement: VoiceAnnouncement):
        """Execute text-to-speech for an announcement"""
        if self.is_speaking:
            return  # Skip if already speaking

        self.is_speaking = True

        try:
            timestamp = announcement.timestamp.strftime("%H:%M:%S")

            # Log announcement
            logger.info(f"🔊 [{timestamp}] {announcement.category.upper()}: {announcement.message}")

            # Add to history
            self.announcement_history.append(announcement)

            # Keep only last 50 announcements
            if len(self.announcement_history) > 50:
                self.announcement_history = self.announcement_history[-50:]

            # Execute TTS based on selected engine
            if self.current_engine == VoiceEngine.SYSTEM_TTS:
                self._system_tts(announcement.message)
            elif self.current_engine == VoiceEngine.PYTTSX3:
                self._pyttsx3_speak(announcement.message)
            elif self.current_engine == VoiceEngine.ESPEAK:
                self._espeak_speak(announcement.message)

        except Exception as e:
            logger.error(f"TTS execution failed: {e}")
        finally:
            self.is_speaking = False

    def _system_tts(self, message: str):
        """Use system TTS (platform-specific)"""
        try:
            if sys.platform == "darwin":  # macOS
                args = ["say", "-r", str(self.voice_settings['rate'])]
                # Only pass -v if user set a voice_id
                if self.voice_settings.get('voice_id'):
                    args += ["-v", self.voice_settings['voice_id']]
                args.append(message)
                subprocess.run(args, check=False, timeout=30)

            elif sys.platform == "win32":  # Windows (via pyttsx3)
                self._pyttsx3_speak(message)

            elif sys.platform.startswith("linux"):  # Linux (espeak)
                args = [
                    "espeak",
                    "-s", str(self.voice_settings['rate']),
                    "-a", str(int(self.voice_settings['volume'] * 200)),
                ]
                if self.voice_settings.get('voice_id'):
                    args += ["-v", self.voice_settings['voice_id']]
                args.append(message)
                subprocess.run(args, check=False, timeout=30)

        except subprocess.TimeoutExpired:
            logger.warning("TTS timeout - message too long")
        except Exception as e:
            logger.error(f"System TTS failed: {e}")

    def _pyttsx3_speak(self, message: str):
        """Use pyttsx3 TTS engine"""
        try:
            import pyttsx3

            engine = pyttsx3.init()

            # Configure voice settings
            engine.setProperty('rate', self.voice_settings['rate'])
            engine.setProperty('volume', self.voice_settings['volume'])

            # Respect explicit voice_id if provided
            if self.voice_settings.get('voice_id'):
                engine.setProperty('voice', self.voice_settings['voice_id'])
            else:
                # Try to choose a professional default voice if available
                voices = engine.getProperty('voices')
                if voices:
                    preferred = [v for v in voices if any(
                        key in (v.name or "") for key in ["Microsoft", "System", "David", "Alex"]
                    )]
                    if preferred:
                        engine.setProperty('voice', preferred[0].id)

            engine.say(message)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            logger.error(f"pyttsx3 TTS failed: {e}")

    def _espeak_speak(self, message: str):
        """Use espeak TTS engine"""
        try:
            args = [
                "espeak",
                "-s", str(self.voice_settings['rate']),
                "-a", str(int(self.voice_settings['volume'] * 200)),
            ]
            if self.voice_settings.get('voice_id'):
                args += ["-v", self.voice_settings['voice_id']]
            args.append(message)
            subprocess.run(args, check=False, timeout=30)

        except Exception as e:
            logger.error(f"espeak TTS failed: {e}")

    def announce(self, message: str, priority: Priority = Priority.NORMAL,
                 category: str = "general") -> bool:
        """
        Add an announcement to the queue

        Args:
            message: Text to speak
            priority: Announcement priority
            category: Category for logging

        Returns:
            bool: True if announcement was queued successfully
        """
        if not self.enabled:
            return False

        try:
            announcement = VoiceAnnouncement(
                message=message,
                priority=priority,
                timestamp=datetime.now(UTC),
                category=category
            )
            # Include a sequence number as tie-breaker to avoid comparing dataclasses
            idx = next(self._seq)
            self.announcement_queue.put((priority.value, idx, announcement))
            return True

        except Exception as e:
            logger.error(f"Failed to queue announcement: {e}")
            return False

    def announce_emergency(self, message: str, category: str = "emergency") -> bool:
        """Quick method for critical emergency announcements"""
        return self.announce(message, Priority.CRITICAL, category)

    def announce_template(self, template_key: str, **kwargs) -> bool:
        """Announce using a predefined template"""
        if template_key not in self.message_templates:
            logger.error(f"Unknown template: {template_key}")
            return False

        try:
            message = self.message_templates[template_key].format(**kwargs)
            priority = Priority.CRITICAL if template_key in [
                'threat_detected', 'earthquake', 'hurricane', 'wildfire'
            ] else Priority.NORMAL

            return self.announce(message, priority, template_key)

        except KeyError as e:
            logger.error(f"Template formatting error: {e}")
            return False

    def set_voice_settings(self, rate: int = None, volume: float = None, voice_id: str = None):
        """Update voice settings"""
        if rate is not None:
            self.voice_settings['rate'] = max(80, min(300, rate))

        if volume is not None:
            self.voice_settings['volume'] = max(0.0, min(1.0, volume))

        if voice_id is not None:
            self.voice_settings['voice_id'] = voice_id

        logger.info(f"Voice settings updated: {self.voice_settings}")

    def enable_voice(self, enabled: bool = True):
        """Enable or disable voice announcements"""
        self.voice_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"Voice announcements {status}")

    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            'queue_size': self.announcement_queue.qsize(),
            'is_speaking': self.is_speaking,
            'enabled': self.enabled,
            'voice_enabled': self.voice_enabled,
            'current_engine': self.current_engine.value,
            'announcements_made': len(self.announcement_history)
        }

    def get_recent_announcements(self, count: int = 10) -> List[Dict]:
        """Get recent announcements"""
        recent = self.announcement_history[-count:] if self.announcement_history else []

        return [
            {
                'message': ann.message,
                'priority': ann.priority.name,
                'category': ann.category,
                'timestamp': ann.timestamp.isoformat()
            }
            for ann in recent
        ]

    def clear_queue(self):
        """Clear all pending announcements"""
        while not self.announcement_queue.empty():
            try:
                self.announcement_queue.get_nowait()
                self.announcement_queue.task_done()
            except queue.Empty:
                break

        logger.info("Announcement queue cleared")

    def stop(self):
        """Stop the voice coordinator"""
        self.stop_event.set()
        self.clear_queue()

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)

        logger.info("Voice coordinator stopped")


class EmergencyAnnouncementSystem:
    """
    High-level emergency announcement system
    Provides predefined emergency scenarios and coordination
    """

    def __init__(self, voice_coordinator: VoiceCoordinator = None):
        self.voice = voice_coordinator or VoiceCoordinator()
        self.active_scenario = None
        self.scenario_start_time = None

    def start_emergency_scenario(self, scenario_type: str, **details):
        """Start an emergency scenario with appropriate announcements"""
        self.active_scenario = scenario_type
        self.scenario_start_time = datetime.now(UTC)

        # Initial emergency alert
        self.voice.announce_emergency(
            f"Emergency activation: {scenario_type}. Initiating autonomous response protocols.",
            "scenario_start"
        )

        # Scenario-specific announcements
        if scenario_type.lower().startswith('earthquake'):
            magnitude = details.get('magnitude', 'unknown')
            location = details.get('location', 'unknown location')

            self.voice.announce_template(
                'earthquake',
                magnitude=magnitude
            )

            # Follow-up announcements
            threading.Timer(5.0, lambda: self.voice.announce(
                f"Earthquake magnitude {magnitude} detected at {location}. "
                f"Structural assessment in progress.",
                Priority.HIGH, "earthquake_details"
            )).start()

        elif scenario_type.lower().startswith('hurricane'):
            category = details.get('category', 'unknown')
            location = details.get('location', 'unknown location')

            self.voice.announce_template(
                'hurricane',
                category=category
            )

            threading.Timer(5.0, lambda: self.voice.announce(
                f"Hurricane category {category} approaching {location}. "
                f"Evacuation coordination initiating.",
                Priority.HIGH, "hurricane_details"
            )).start()

        elif scenario_type.lower().startswith('wildfire'):
            location = details.get('location', 'unknown location')

            self.voice.announce_template('wildfire')

            threading.Timer(5.0, lambda: self.voice.announce(
                f"Wildfire detected at {location}. "
                f"Fire suppression resources deploying.",
                Priority.HIGH, "wildfire_details"
            )).start()

    def announce_response_phase(self, phase: str, details: str = ""):
        """Announce response phase transitions"""
        phase_messages = {
            'threat_detection': "Phase 1: Multi-source threat detection and analysis in progress",
            'resource_optimization': "Phase 2: Resource deployment optimization active",
            'emergency_communications': "Phase 3: Emergency communications and citizen alerts deploying",
            'impact_assessment': "Phase 4: Impact assessment and coordination finalization"
        }

        message = phase_messages.get(phase, f"Response phase: {phase}")
        if details:
            message += f". {details}"

        self.voice.announce(message, Priority.HIGH, f"phase_{phase}")

    def announce_coordination_update(self, agents_active: int = 3, decisions_made: int = 0,
                                     population_reached: int = 0):
        """Announce coordination status updates"""
        if decisions_made > 0:
            self.voice.announce(
                f"AI coordination update: {decisions_made} autonomous decisions made. "
                f"{agents_active} agents active.",
                Priority.NORMAL, "coordination_update"
            )

        if population_reached > 0:
            self.voice.announce_template(
                'population_alert',
                count=f"{population_reached:,}"
            )

    def announce_completion(self, lives_protected: int = 0, response_time: float = 0,
                            economic_impact: float = 0):
        """Announce successful response completion"""
        if lives_protected > 0:
            self.voice.announce_template(
                'response_complete',
                lives=f"{lives_protected:,}"
            )

        # Additional completion details
        details = []
        if response_time > 0:
            details.append(f"Response time: {response_time:.1f} seconds")
        if economic_impact > 0:
            details.append(f"Economic loss prevented: ${economic_impact:.1f} billion")

        if details:
            self.voice.announce(
                f"Mission metrics: {'. '.join(details)}.",
                Priority.NORMAL, "completion_metrics"
            )

        # Final status
        self.voice.announce(
            "DisasterShield autonomous response complete. All systems standing by for next emergency.",
            Priority.NORMAL, "system_ready"
        )

    def get_scenario_status(self) -> Dict:
        """Get current scenario status"""
        runtime = None
        if self.scenario_start_time:
            runtime = (datetime.now(UTC) - self.scenario_start_time).total_seconds()

        return {
            'active_scenario': self.active_scenario,
            'scenario_runtime_seconds': runtime,
            'voice_status': self.voice.get_queue_status(),
            'recent_announcements': self.voice.get_recent_announcements(5)
        }


# Convenience functions for easy integration
def create_voice_coordinator(enabled: bool = True) -> VoiceCoordinator:
    """Create and initialize a voice coordinator"""
    return VoiceCoordinator(enabled=enabled)


def create_emergency_system(enabled: bool = True) -> EmergencyAnnouncementSystem:
    """Create and initialize an emergency announcement system"""
    voice = VoiceCoordinator(enabled=enabled)
    return EmergencyAnnouncementSystem(voice)


# Demo and testing functions
def test_voice_system():
    """Test the voice coordination system"""
    print("Testing DisasterShield Voice Coordination System...")

    voice = VoiceCoordinator(enabled=True)

    # Test basic announcement
    voice.announce("Voice coordination system test initiated", Priority.NORMAL, "test")

    # Test template
    voice.announce_template('system_start')

    # Test emergency
    voice.announce_emergency("This is a test emergency announcement")

    # Wait for announcements to complete
    time.sleep(5)

    # Show status
    status = voice.get_queue_status()
    print(f"Queue status: {status}")

    recent = voice.get_recent_announcements(3)
    print(f"Recent announcements: {len(recent)}")

    voice.stop()
    print("Voice system test complete")


def demo_emergency_scenario():
    """Demonstrate emergency scenario announcements"""
    print("Demonstrating Emergency Scenario...")

    emergency_system = create_emergency_system(enabled=True)

    # Start earthquake scenario
    emergency_system.start_emergency_scenario(
        "Earthquake M6.2",
        magnitude=6.2,
        location="San Francisco Bay Area"
    )

    # Simulate response phases
    time.sleep(3)
    emergency_system.announce_response_phase('threat_detection')

    time.sleep(2)
    emergency_system.announce_response_phase('resource_optimization')

    time.sleep(2)
    emergency_system.announce_coordination_update(
        agents_active=3,
        decisions_made=15,
        population_reached=185000
    )

    time.sleep(2)
    emergency_system.announce_response_phase('emergency_communications')

    time.sleep(3)
    emergency_system.announce_completion(
        lives_protected=1866,
        response_time=45.2,
        economic_impact=37.3
    )

    # Show final status
    status = emergency_system.get_scenario_status()
    print(f"Scenario completed: {status}")

    emergency_system.voice.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DisasterShield Voice Coordinator")
    parser.add_argument('--test', action='store_true', help='Run voice system test')
    parser.add_argument('--demo', action='store_true', help='Run emergency scenario demo')
    parser.add_argument('--message', type=str, help='Speak a custom message')
    # Optional: allow overriding voice id from CLI (macOS: "Alex", Linux espeak e.g. "en+m3")
    parser.add_argument('--voice-id', type=str, help='Override TTS voice id')
    parser.add_argument('--mute', action='store_true', help='Disable actual TTS output')

    args = parser.parse_args()

    if args.test:
        test_voice_system()
    elif args.demo:
        demo_emergency_scenario()
    elif args.message:
        voice = VoiceCoordinator(enabled=True)
        if args.voice_id:
            voice.set_voice_settings(voice_id=args.voice_id)
        if args.mute:
            voice.enable_voice(False)
        voice.announce(args.message, Priority.NORMAL, "custom")
        time.sleep(3)
        voice.stop()
    else:
        print("DisasterShield Voice Coordinator")
        print("Use --test, --demo, or --message 'text' options")
        print("Optional: --voice-id Alex (macOS) | --mute")