#include "MidiGenerator.h"

juce::MidiBuffer MidiGenerator::generateOffline(float bpm, float complexity, float rollProb, const juce::String& style) {
    juce::MidiBuffer buffer;
    
    double secondsPerBeat = 60.0 / bpm;
    double secondsPer16th = secondsPerBeat / 4.0;
    
    int numSteps = 16;
    for (int bar = 0; bar < 4; ++bar) {
        for (int i = 0; i < numSteps; ++i) {
            bool play = false;
            if (complexity >= 0.8f) play = true;
            else if (complexity >= 0.4f && i % 2 == 0) play = true;
            else if (i % 4 == 0) play = true;
            
            if (play) {
                double time = (bar * 16 + i) * secondsPer16th;
                int samplePos = (int)(time * 44100.0); 
                juce::MidiMessage msgOn = juce::MidiMessage::noteOn(1, 42, 0.8f);
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
