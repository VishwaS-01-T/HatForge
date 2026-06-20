#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class HatForgeAudioProcessorEditor  : public juce::AudioProcessorEditor
{
public:
    HatForgeAudioProcessorEditor (HatForgeAudioProcessor&);
    ~HatForgeAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    HatForgeAudioProcessor& audioProcessor;
    
    juce::Slider complexitySlider;
    juce::Slider rollProbSlider;
    juce::Slider openHatSlider;
    juce::Slider humanizeSlider;
    
    juce::TextEditor promptEditor;
    juce::TextButton generateBtn{"GENERATE HATS"};
    juce::Label statusLabel{"status", "Status: Ready"};
    
    juce::ToggleButton aiToggle{"Use AI Server"};
    juce::TextEditor serverEditor;
    juce::TextButton connectBtn{"CONNECT"};
    juce::TextButton testBtn{"TEST"};
    
    using Attachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    std::unique_ptr<Attachment> complexityAttachment;
    std::unique_ptr<Attachment> rollProbAttachment;
    std::unique_ptr<Attachment> openHatAttachment;
    std::unique_ptr<Attachment> humanizeAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (HatForgeAudioProcessorEditor)
};
