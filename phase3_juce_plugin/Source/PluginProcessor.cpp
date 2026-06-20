#include "PluginProcessor.h"
#include "PluginEditor.h"

// ── Parameter ID constants ──
const juce::String HatForgeAudioProcessor::COMPLEXITY_ID = "complexity";
const juce::String HatForgeAudioProcessor::ROLLS_ID      = "rolls";
const juce::String HatForgeAudioProcessor::HUMANIZE_ID   = "humanize";
const juce::String HatForgeAudioProcessor::OPEN_HAT_ID   = "open_hat";

//==============================================================================
// Constructor / Destructor
//==============================================================================

HatForgeAudioProcessor::HatForgeAudioProcessor()
    : AudioProcessor (BusesProperties()
                          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      parameters (*this, nullptr, juce::Identifier ("HatForgeParams"), createParameterLayout())
{
    aiBridge = std::make_unique<AIBridge>();
    midiGen  = std::make_unique<MidiGenerator>();

    startWorkerThread();
}

HatForgeAudioProcessor::~HatForgeAudioProcessor()
{
    stopWorkerThread();

    // Clean up any un-consumed ready sequence
    auto* seq = readySequence.exchange (nullptr);
    delete seq;
}

//==============================================================================
// Metadata
//==============================================================================

const juce::String HatForgeAudioProcessor::getName() const            { return "HatForge"; }
bool               HatForgeAudioProcessor::acceptsMidi() const        { return true; }
bool               HatForgeAudioProcessor::producesMidi() const       { return true; }
bool               HatForgeAudioProcessor::isMidiEffect() const       { return false; }
double             HatForgeAudioProcessor::getTailLengthSeconds() const { return 0.0; }
int                HatForgeAudioProcessor::getNumPrograms()           { return 1; }
int                HatForgeAudioProcessor::getCurrentProgram()        { return 0; }
void               HatForgeAudioProcessor::setCurrentProgram (int)    {}
const juce::String HatForgeAudioProcessor::getProgramName (int)       { return {}; }
void               HatForgeAudioProcessor::changeProgramName (int, const juce::String&) {}

//==============================================================================
// Prepare / Release
//==============================================================================

void HatForgeAudioProcessor::prepareToPlay (double sampleRate, int /*samplesPerBlock*/)
{
    hostSampleRate = sampleRate;
    juce::Logger::writeToLog ("HatForge ready at " + juce::String (sampleRate) + " Hz");
}

void HatForgeAudioProcessor::releaseResources() {}

bool HatForgeAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    auto mainOut = layouts.getMainOutputChannelSet();
    return mainOut == juce::AudioChannelSet::mono()
        || mainOut == juce::AudioChannelSet::stereo();
}

//==============================================================================
// processBlock — AUDIO THREAD
//
// 1. Read the DAW transport position.
// 2. Pick up any newly generated MIDI from the worker thread (atomic swap).
// 3. Walk through the active MIDI sequence and emit events whose timestamps
//    fall within the current block's PPQ window.
//==============================================================================

void HatForgeAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    buffer.clear();

    // ── 1. Read transport ──
    double blockStartPpq = 0.0;
    double blockEndPpq   = 0.0;
    bool   isPlaying     = false;

    if (auto* playHead = getPlayHead())
    {
        if (auto pos = playHead->getPosition())
        {
            if (pos->getBpm().hasValue())
                playbackState.bpm.store ((float) *pos->getBpm(), std::memory_order_relaxed);

            if (pos->getIsPlaying())
                isPlaying = *pos->getIsPlaying();

            if (pos->getPpqPosition().hasValue())
            {
                blockStartPpq = *pos->getPpqPosition();
                playbackState.currentBar.store ((int)(blockStartPpq / 4.0), std::memory_order_relaxed);

                // Calculate the PPQ length of this audio block
                double bpm = (double) playbackState.bpm.load (std::memory_order_relaxed);
                if (bpm <= 0.0) bpm = 120.0;
                double beatsPerSample = bpm / (60.0 * hostSampleRate);
                blockEndPpq = blockStartPpq + beatsPerSample * buffer.getNumSamples();
            }
        }
    }

    // ── 2. Accumulate incoming drum MIDI for context (used by worker) ──
    incomingDrumMidi.addEvents (midiMessages, 0, buffer.getNumSamples(), 0);

    // ── 3. Pick up new MIDI from worker (lock-free) ──
    auto* newSeq = readySequence.exchange (nullptr, std::memory_order_acquire);
    if (newSeq != nullptr)
    {
        activeSequence.reset (newSeq);
        activeSequenceIndex = 0;
        sequenceStartPpq = blockStartPpq; // anchor playback to NOW
    }

    // ── 4. Emit MIDI events from the active sequence ──
    if (activeSequence != nullptr && isPlaying && sequenceStartPpq >= 0.0)
    {
        double bpm = (double) playbackState.bpm.load (std::memory_order_relaxed);
        if (bpm <= 0.0) bpm = 120.0;
        double beatsPerSecond = bpm / 60.0;

        int numEvents = activeSequence->getNumEvents();

        while (activeSequenceIndex < numEvents)
        {
            auto* evPtr = activeSequence->getEventPointer (activeSequenceIndex);
            double eventTimeSec = evPtr->message.getTimeStamp(); // seconds from start
            double eventPpq = sequenceStartPpq + eventTimeSec * beatsPerSecond;

            if (eventPpq >= blockEndPpq)
                break; // this event belongs to a future block

            if (eventPpq >= blockStartPpq)
            {
                // Map PPQ offset within this block to a sample offset
                double ppqOffset   = eventPpq - blockStartPpq;
                double ppqPerBlock = blockEndPpq - blockStartPpq;
                int sampleOffset = 0;
                if (ppqPerBlock > 0.0)
                    sampleOffset = juce::jlimit (0,
                                                 buffer.getNumSamples() - 1,
                                                 (int) (ppqOffset / ppqPerBlock * buffer.getNumSamples()));

                midiMessages.addEvent (evPtr->message, sampleOffset);
            }

            ++activeSequenceIndex;
        }

        // If we've played all events, clear the sequence
        if (activeSequenceIndex >= numEvents)
        {
            activeSequence.reset();
            activeSequenceIndex = 0;
            sequenceStartPpq = -1.0;
        }
    }
}

//==============================================================================
// Editor
//==============================================================================

juce::AudioProcessorEditor* HatForgeAudioProcessor::createEditor()
{
    return new HatForgeAudioProcessorEditor (*this);
}

bool HatForgeAudioProcessor::hasEditor() const { return true; }

//==============================================================================
// State
//==============================================================================

void HatForgeAudioProcessor::getStateInformation (juce::MemoryBlock& /*destData*/) {}
void HatForgeAudioProcessor::setStateInformation (const void* /*data*/, int /*sizeInBytes*/) {}

//==============================================================================
// triggerGeneration — called from the GUI thread
//
// Snapshots all parameters and sets the pendingRequest flag.
// The background worker thread will pick it up.
//==============================================================================

void HatForgeAudioProcessor::triggerGeneration (const juce::String& prompt)
{
    if (isGenerating.load (std::memory_order_relaxed))
        return;

    // Snapshot parameters (all atomic or GUI-thread-safe reads)
    playbackState.prompt = prompt;
    requestPrompt     = playbackState.prompt;
    requestBPM        = playbackState.bpm.load (std::memory_order_relaxed);
    requestComplexity = parameters.getRawParameterValue (COMPLEXITY_ID)->load();
    requestRolls      = parameters.getRawParameterValue (ROLLS_ID)->load();
    requestUseAI      = useAIServer;
    requestMidiB64    = midiGen->toBase64 (incomingDrumMidi);

    // Signal the worker
    isGenerating.store (true, std::memory_order_relaxed);
    pendingRequest.store (true, std::memory_order_release);
}

void HatForgeAudioProcessor::setBPMFromHost (double bpm)
{
    playbackState.bpm.store ((float) bpm, std::memory_order_relaxed);
}

//==============================================================================
// Background worker thread
//==============================================================================

void HatForgeAudioProcessor::startWorkerThread()
{
    workerShouldRun.store (true, std::memory_order_relaxed);
    workerThread = std::thread ([this] { workerLoop(); });
}

void HatForgeAudioProcessor::stopWorkerThread()
{
    workerShouldRun.store (false, std::memory_order_relaxed);
    if (workerThread.joinable())
        workerThread.join();
}

void HatForgeAudioProcessor::workerLoop()
{
    while (workerShouldRun.load (std::memory_order_relaxed))
    {
        // Sleep 50 ms between polls — generation requests are infrequent
        std::this_thread::sleep_for (std::chrono::milliseconds (50));

        if (! pendingRequest.load (std::memory_order_acquire))
            continue;

        pendingRequest.store (false, std::memory_order_relaxed);

        // ── Execute the generation ──
        juce::MidiBuffer resultBuffer;

        if (requestUseAI && aiBridge->connect ("127.0.0.1", 7891))
        {
            // Build the JSON payload
            juce::var params (new juce::DynamicObject());
            auto* paramsObj = params.getDynamicObject();
            paramsObj->setProperty ("complexity", requestComplexity);
            paramsObj->setProperty ("rolls",      requestRolls);

            juce::var payload (new juce::DynamicObject());
            auto* payloadObj = payload.getDynamicObject();
            payloadObj->setProperty ("bpm",      (double) requestBPM);
            payloadObj->setProperty ("midi_b64", requestMidiB64);
            payloadObj->setProperty ("prompt",   requestPrompt);
            payloadObj->setProperty ("params",   params);

            juce::String responseStr = aiBridge->sendRequest (payload);

            auto response = juce::JSON::parse (responseStr);
            if (response.isObject() && response["status"] == "ok")
            {
                juce::String b64 = response["midi_b64"].toString();
                resultBuffer = midiGen->fromBase64 (b64);
            }
        }
        else
        {
            // Offline / rule-based fallback
            resultBuffer = midiGen->generateOffline (requestBPM,
                                                     requestComplexity,
                                                     requestRolls,
                                                     requestPrompt);
        }

        // ── Convert MidiBuffer → MidiMessageSequence (time in seconds) ──
        auto* seq = new juce::MidiMessageSequence();
        for (const auto metadata : resultBuffer)
        {
            auto msg = metadata.getMessage();
            // MidiGenerator stores timestamps in seconds already via
            // setTimeStamp, but the buffer sample positions are also set.
            // We use the message timestamp (seconds) as the authoritative time.
            double timeSec = msg.getTimeStamp();
            if (timeSec <= 0.0)
            {
                // Fall back to deriving from sample position
                timeSec = (double) metadata.samplePosition / hostSampleRate;
            }
            msg.setTimeStamp (timeSec);
            seq->addEvent (msg);
        }
        seq->updateMatchedPairs();
        seq->sort();

        // ── Publish to the audio thread (lock-free) ──
        auto* old = readySequence.exchange (seq, std::memory_order_release);
        delete old; // clean up any previously-unread sequence

        incomingDrumMidi.clear();
        isGenerating.store (false, std::memory_order_relaxed);
    }
}

//==============================================================================
// Parameters
//==============================================================================

juce::AudioProcessorValueTreeState::ParameterLayout
HatForgeAudioProcessor::createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;

    params.push_back (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID (COMPLEXITY_ID, 1), "Complexity", 0.0f, 1.0f, 0.5f));

    params.push_back (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID (ROLLS_ID, 1), "Roll Probability", 0.0f, 1.0f, 0.3f));

    params.push_back (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID (OPEN_HAT_ID, 1), "Open Hat", 0.0f, 1.0f, 0.15f));

    params.push_back (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID (HUMANIZE_ID, 1), "Humanize", 0.0f, 1.0f, 0.3f));

    return { params.begin(), params.end() };
}

//==============================================================================
// Plugin instantiation
//==============================================================================

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new HatForgeAudioProcessor();
}
