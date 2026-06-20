#pragma once

#include <JuceHeader.h>
#include "AIBridge.h"
#include "MidiGenerator.h"

#include <atomic>
#include <thread>
#include <mutex>

/**
 * HatForgeAudioProcessor
 *
 * Architecture overview:
 *
 *   GUI Thread                 Worker Thread               Audio Thread
 *  ┌──────────┐              ┌──────────────┐            ┌────────────┐
 *  │ trigger   │── request ──▸│ connect +    │── result ──▸│ processBlock│
 *  │ Generation│  (atomic)    │ sendRequest  │  (swap ptr) │ reads MIDI │
 *  └──────────┘              └──────────────┘            └────────────┘
 *
 * - The GUI calls triggerGeneration() which sets a flag for the worker.
 * - The worker thread runs the TCP call off the audio thread.
 * - The result is exchanged into the processor via an atomic pointer swap.
 * - processBlock() reads the DAW position and emits MIDI only for events
 *   whose timestamps fall within the current audio block's time window.
 */
class HatForgeAudioProcessor : public juce::AudioProcessor
{
public:
    HatForgeAudioProcessor();
    ~HatForgeAudioProcessor() override;

    // ── AudioProcessor overrides ──
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override;

    const juce::String getName() const override;
    bool acceptsMidi() const override;
    bool producesMidi() const override;
    bool isMidiEffect() const override;
    double getTailLengthSeconds() const override;

    int getNumPrograms() override;
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override;
    const juce::String getProgramName (int index) override;
    void changeProgramName (int index, const juce::String& newName) override;

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    // ── HatForge public API ──

    /** Called from the GUI thread. Pushes a generation request to the worker. */
    void triggerGeneration (const juce::String& prompt);

    void setBPMFromHost (double bpm);

    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    // Parameter tree
    juce::AudioProcessorValueTreeState parameters;

    struct PlaybackState {
        std::atomic<float> bpm { 120.0f };
        std::atomic<int>   currentBar { 0 };
        juce::String       prompt { "trap" };
    };

    // State visible to the editor
    PlaybackState      playbackState;
    std::atomic<bool>  isGenerating { false };
    bool               useAIServer { true };

    // Incoming drum MIDI accumulated from the host for context
    juce::MidiBuffer incomingDrumMidi;

    // Subsystems
    std::unique_ptr<AIBridge>      aiBridge;
    std::unique_ptr<MidiGenerator> midiGen;

    // Parameter IDs
    static const juce::String COMPLEXITY_ID;
    static const juce::String ROLLS_ID;
    static const juce::String HUMANIZE_ID;
    static const juce::String OPEN_HAT_ID;

private:
    // ── Background worker ──
    void startWorkerThread();
    void stopWorkerThread();
    void workerLoop();

    std::thread        workerThread;
    std::atomic<bool>  workerShouldRun { false };
    std::atomic<bool>  pendingRequest  { false };

    // Data passed to the worker (written by GUI, read by worker)
    juce::String       requestPrompt;
    float              requestBPM       { 120.0f };
    float              requestComplexity{ 0.5f };
    float              requestRolls     { 0.3f };
    bool               requestUseAI     { true };
    juce::String       requestMidiB64;

    // ── Lock-free MIDI result exchange ──
    // The worker produces a MidiMessageSequence (sorted by time in seconds).
    // It writes the pointer atomically; processBlock() picks it up.
    std::atomic<juce::MidiMessageSequence*> readySequence { nullptr };

    // The sequence currently being played back by the audio thread.
    std::unique_ptr<juce::MidiMessageSequence> activeSequence;
    int activeSequenceIndex { 0 };   // next event index to emit
    double sequenceStartPpq { -1.0 }; // PPQ at which we started playback

    // Stored sample rate for timing calculations
    double hostSampleRate { 44100.0 };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (HatForgeAudioProcessor)
};
