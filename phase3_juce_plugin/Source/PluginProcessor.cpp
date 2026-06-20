#include "PluginProcessor.h"
#include "PluginEditor.h"

const juce::String HatForgeAudioProcessor::COMPLEXITY_ID = "complexity";
const juce::String HatForgeAudioProcessor::ROLLS_ID = "rolls";
const juce::String HatForgeAudioProcessor::HUMANIZE_ID = "humanize";
const juce::String HatForgeAudioProcessor::OPEN_HAT_ID = "open_hat";

HatForgeAudioProcessor::HatForgeAudioProcessor()
     : AudioProcessor (BusesProperties()
                       .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                       .withOutput ("Output", juce::AudioChannelSet::stereo(), true)
                       ),
       parameters(*this, nullptr, juce::Identifier("HatForgeParams"), createParameterLayout())
{
    aiBridge = std::make_unique<AIBridge>();
    midiGen = std::make_unique<MidiGenerator>();
}

HatForgeAudioProcessor::~HatForgeAudioProcessor() {}

const juce::String HatForgeAudioProcessor::getName() const { return "HatForge"; }
bool HatForgeAudioProcessor::acceptsMidi() const { return true; }
bool HatForgeAudioProcessor::producesMidi() const { return true; }
bool HatForgeAudioProcessor::isMidiEffect() const { return false; }
double HatForgeAudioProcessor::getTailLengthSeconds() const { return 0.0; }
int HatForgeAudioProcessor::getNumPrograms() { return 1; }
int HatForgeAudioProcessor::getCurrentProgram() { return 0; }
void HatForgeAudioProcessor::setCurrentProgram (int) {}
const juce::String HatForgeAudioProcessor::getProgramName (int) { return {}; }
void HatForgeAudioProcessor::changeProgramName (int, const juce::String&) {}

void HatForgeAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock) {
    juce::Logger::writeToLog("HatForge ready at " + juce::String(sampleRate) + "Hz");
}

void HatForgeAudioProcessor::releaseResources() {}

bool HatForgeAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const {
    if (layouts.getMainOutputChannelSet() != juce::AudioChannelSet::mono()
     && layouts.getMainOutputChannelSet() != juce::AudioChannelSet::stereo())
        return false;
    return true;
}

void HatForgeAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages) {
    buffer.clear();
    
    if (auto* playHead = getPlayHead()) {
        if (auto pos = playHead->getPosition()) {
            if (pos->getBpm().hasValue()) {
                currentBPM = *pos->getBpm();
            }
            if (pos->getPpqPosition().hasValue()) {
                currentBar = (int)(*pos->getPpqPosition() / 4.0);
            }
        }
    }
    
    incomingDrumMidi.addEvents(midiMessages, 0, buffer.getNumSamples(), 0);
    
    if (!generatedHatMidi.isEmpty()) {
        midiMessages.addEvents(generatedHatMidi, 0, buffer.getNumSamples(), 0);
        generatedHatMidi.clear();
    }
}

bool HatForgeAudioProcessor::hasEditor() const { return true; }

void HatForgeAudioProcessor::getStateInformation (juce::MemoryBlock& destData) {}
void HatForgeAudioProcessor::setStateInformation (const void* data, int sizeInBytes) {}

void HatForgeAudioProcessor::triggerGeneration(const juce::String& prompt) {
    if (isGenerating) return;
    isGenerating = true;
    currentPrompt = prompt;
    
    std::thread([this]() {
        juce::var params(new juce::DynamicObject());
        auto* obj = params.getDynamicObject();
        obj->setProperty("complexity", parameters.getRawParameterValue(COMPLEXITY_ID)->load());
        obj->setProperty("rolls", parameters.getRawParameterValue(ROLLS_ID)->load());
        
        juce::var payload(new juce::DynamicObject());
        auto* payloadObj = payload.getDynamicObject();
        payloadObj->setProperty("bpm", currentBPM);
        payloadObj->setProperty("midi_b64", midiGen->toBase64(incomingDrumMidi));
        payloadObj->setProperty("prompt", currentPrompt);
        payloadObj->setProperty("params", params);
        
        if (useAIServer && aiBridge->connect("127.0.0.1", 7891)) {
            juce::String responseStr = aiBridge->sendRequest(payload);
            juce::var response;
            juce::JSON::parse(responseStr, response);
            if (response.isObject() && response["status"] == "ok") {
                juce::String b64 = response["midi_b64"].toString();
                auto generated = midiGen->fromBase64(b64);
                
                juce::ScopedLock sl(getCallbackLock());
                generatedHatMidi.addEvents(generated, 0, -1, 0);
            }
        } else {
            auto generated = midiGen->generateOffline(currentBPM, parameters.getRawParameterValue(COMPLEXITY_ID)->load(), parameters.getRawParameterValue(ROLLS_ID)->load(), currentPrompt);
            juce::ScopedLock sl(getCallbackLock());
            generatedHatMidi.addEvents(generated, 0, -1, 0);
        }
        
        incomingDrumMidi.clear();
        isGenerating = false;
    }).detach();
}

void HatForgeAudioProcessor::setBPMFromHost(double bpm) { currentBPM = bpm; }
juce::MidiBuffer& HatForgeAudioProcessor::getGeneratedMidi() { return generatedHatMidi; }

juce::AudioProcessorValueTreeState::ParameterLayout HatForgeAudioProcessor::createParameterLayout() {
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    
    params.push_back(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(COMPLEXITY_ID, 1), "Complexity", 0.0f, 1.0f, 0.5f));
    params.push_back(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(ROLLS_ID, 1), "Roll Probability", 0.0f, 1.0f, 0.3f));
    params.push_back(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(OPEN_HAT_ID, 1), "Open Hat", 0.0f, 1.0f, 0.15f));
    params.push_back(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(HUMANIZE_ID, 1), "Humanize", 0.0f, 1.0f, 0.3f));
    
    return { params.begin(), params.end() };
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() {
    return new HatForgeAudioProcessor();
}
