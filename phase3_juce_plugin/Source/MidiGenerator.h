#pragma once

#include <JuceHeader.h>

class MidiGenerator {
public:
    MidiGenerator() = default;
    
    juce::MidiBuffer generateOffline(float bpm, float complexity, float rollProb, const juce::String& style);
    
    juce::MidiBuffer fromBase64(const juce::String& b64MidiData);
    juce::String toBase64(const juce::MidiBuffer& buffer);
};
