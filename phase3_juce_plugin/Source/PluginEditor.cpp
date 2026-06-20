#include "PluginEditor.h"

HatForgeAudioProcessorEditor::HatForgeAudioProcessorEditor (HatForgeAudioProcessor& p)
    : AudioProcessorEditor (&p), audioProcessor (p)
{
    setSize (800, 500);

    addAndMakeVisible(complexitySlider);
    complexitySlider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
    complexitySlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    complexityAttachment = std::make_unique<Attachment>(audioProcessor.parameters, audioProcessor.COMPLEXITY_ID, complexitySlider);

    addAndMakeVisible(rollProbSlider);
    rollProbSlider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
    rollProbSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    rollProbAttachment = std::make_unique<Attachment>(audioProcessor.parameters, audioProcessor.ROLLS_ID, rollProbSlider);

    addAndMakeVisible(openHatSlider);
    openHatSlider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
    openHatSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    openHatAttachment = std::make_unique<Attachment>(audioProcessor.parameters, audioProcessor.OPEN_HAT_ID, openHatSlider);

    addAndMakeVisible(humanizeSlider);
    humanizeSlider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
    humanizeSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    humanizeAttachment = std::make_unique<Attachment>(audioProcessor.parameters, audioProcessor.HUMANIZE_ID, humanizeSlider);

    addAndMakeVisible(promptEditor);
    promptEditor.setText("dark rage");

    addAndMakeVisible(generateBtn);
    generateBtn.onClick = [this]() {
        audioProcessor.triggerGeneration(promptEditor.getText());
    };

    addAndMakeVisible(statusLabel);

    addAndMakeVisible(aiToggle);
    aiToggle.setToggleState(audioProcessor.useAIServer, juce::dontSendNotification);
    aiToggle.onClick = [this]() { audioProcessor.useAIServer = aiToggle.getToggleState(); };

    addAndMakeVisible(serverEditor);
    serverEditor.setText("127.0.0.1:7891");

    addAndMakeVisible(connectBtn);
    addAndMakeVisible(testBtn);
}

HatForgeAudioProcessorEditor::~HatForgeAudioProcessorEditor() {}

void HatForgeAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (juce::Colours::darkgrey);
    g.setColour (juce::Colours::white);
    g.setFont (15.0f);
    g.drawText ("HatForge BPM: " + juce::String(audioProcessor.currentBPM), getLocalBounds().withTrimmedTop(10).withTrimmedRight(10), juce::Justification::topRight, true);
}

void HatForgeAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(20);
    
    auto leftArea = area.removeFromLeft(200);
    complexitySlider.setBounds(leftArea.removeFromTop(100));
    rollProbSlider.setBounds(leftArea.removeFromTop(100));
    openHatSlider.setBounds(leftArea.removeFromTop(100));
    humanizeSlider.setBounds(leftArea.removeFromTop(100));
    
    auto rightArea = area.withTrimmedLeft(20);
    promptEditor.setBounds(rightArea.removeFromTop(40));
    rightArea.removeFromTop(20);
    generateBtn.setBounds(rightArea.removeFromTop(40));
    rightArea.removeFromTop(20);
    statusLabel.setBounds(rightArea.removeFromTop(30));
    rightArea.removeFromTop(20);
    aiToggle.setBounds(rightArea.removeFromTop(30));
    serverEditor.setBounds(rightArea.removeFromTop(30));
    
    auto btns = rightArea.removeFromTop(30);
    connectBtn.setBounds(btns.removeFromLeft(100));
    testBtn.setBounds(btns.removeFromLeft(100).withTrimmedLeft(10));
}
