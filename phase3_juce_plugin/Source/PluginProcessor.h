#pragma once

#include <JuceHeader.h>
#include "AIBridge.h"
#include "MidiGenerator.h"

class HatForgeAudioProcessor  : public juce::AudioProcessor
{
public:
    HatForgeAudioProcessor();
    ~HatForgeAudioProcessor() override;

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
    
    void triggerGeneration(const juce::String& prompt);
    void setBPMFromHost(double bpm);
    juce::MidiBuffer& getGeneratedMidi();
    
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    juce::AudioProcessorValueTreeState parameters;

    float currentBPM = 120.0f;
    int currentBar = 0;
    bool isGenerating = false;
    juce::String currentPrompt = "trap";
    bool useAIServer = true;

    juce::MidiBuffer incomingDrumMidi;
    juce::MidiBuffer generatedHatMidi;

    std::unique_ptr<AIBridge> aiBridge;
    std::unique_ptr<MidiGenerator> midiGen;

    static const juce::String COMPLEXITY_ID;
    static const juce::String ROLLS_ID;
    static const juce::String HUMANIZE_ID;
    static const juce::String OPEN_HAT_ID;

private:
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (HatForgeAudioProcessor)
};
