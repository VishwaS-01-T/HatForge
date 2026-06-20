#include "MidiGenerator.h"

juce::MidiBuffer MidiGenerator::generateOffline(float bpm, float complexity, float rollProb, const juce::String& style) {
    juce::MidiBuffer buffer;
    
    double secondsPerBeat = 60.0 / bpm;
    double secondsPer16th = secondsPerBeat / 4.0;
    
    // Euclidean rhythm parameters
    int n = 16; // 16 steps per bar
    int k = juce::jlimit(1, 16, (int)(complexity * 16.0f)); // Hits per bar
    
    for (int bar = 0; bar < 4; ++bar) {
        for (int i = 0; i < n; ++i) {
            // Euclidean rhythm condition: (step * hits) % steps < hits
            bool isHit = ((i * k) % n) < k;
            
            if (isHit) {
                // Determine if we should add a roll (32nd note before the hit)
                bool isRoll = (juce::Random::getSystemRandom().nextFloat() < rollProb) && (i % 4 != 0); // avoid rolls exactly on downbeats
                
                double time = (bar * 16 + i) * secondsPer16th;
                int samplePos = (int)(time * 44100.0); 
                
                if (isRoll) {
                    double rollTime = time - (secondsPer16th * 0.5);
                    if (rollTime > 0.0) {
                        int rollSamplePos = (int)(rollTime * 44100.0);
                        juce::MidiMessage msgOn = juce::MidiMessage::noteOn(1, 42, 0.6f);
                        msgOn.setTimeStamp(rollTime);
                        buffer.addEvent(msgOn, rollSamplePos);
                        
                        juce::MidiMessage msgOff = juce::MidiMessage::noteOff(1, 42);
                        msgOff.setTimeStamp(rollTime + secondsPer16th * 0.25);
                        buffer.addEvent(msgOff, rollSamplePos + (int)(secondsPer16th * 0.25 * 44100.0));
                    }
                }
                
                // Add the main hit with slight humanized velocity
                float velocity = 0.8f + (juce::Random::getSystemRandom().nextFloat() * 0.2f - 0.1f);
                juce::MidiMessage msgOn = juce::MidiMessage::noteOn(1, 42, velocity);
                msgOn.setTimeStamp(time);
                buffer.addEvent(msgOn, samplePos);
                
                juce::MidiMessage msgOff = juce::MidiMessage::noteOff(1, 42);
                msgOff.setTimeStamp(time + secondsPer16th * 0.5);
                buffer.addEvent(msgOff, samplePos + (int)(secondsPer16th * 0.5 * 44100.0));
            }
        }
    }
    
    return buffer;
}

juce::MidiBuffer MidiGenerator::fromBase64(const juce::String& b64MidiData) {
    juce::MidiBuffer buffer;
    juce::MemoryOutputStream mos;
    if (juce::Base64::convertFromBase64(mos, b64MidiData)) {
        juce::MemoryInputStream mis(mos.getData(), mos.getDataSize(), false);
        juce::MidiFile midiFile;
        if (midiFile.readFrom(mis)) {
            midiFile.convertTimestampTicksToSeconds();
            for (int i = 0; i < midiFile.getNumTracks(); ++i) {
                const auto* track = midiFile.getTrack(i);
                for (int j = 0; j < track->getNumEvents(); ++j) {
                    auto ev = track->getEventPointer(j);
                    int samplePos = (int)(ev->message.getTimeStamp() * 44100.0);
                    buffer.addEvent(ev->message, samplePos);
                }
            }
        }
    }
    return buffer;
}

juce::String MidiGenerator::toBase64(const juce::MidiBuffer& buffer) {
    juce::MidiFile midiFile;
    midiFile.setTicksPerQuarterNote(960);
    juce::MidiMessageSequence seq;
    for (const auto meta : buffer) {
        auto msg = meta.getMessage();
        msg.setTimeStamp(msg.getTimeStamp() / 44100.0); // Simple assuming timestamps are sample pos
        seq.addEvent(msg);
    }
    seq.updateMatchedPairs();
    midiFile.addTrack(seq);
    
    juce::MemoryOutputStream mos;
    midiFile.writeTo(mos);
    
    return juce::Base64::toBase64(mos.getData(), mos.getDataSize());
}
