#pragma once

#include <JuceHeader.h>

class AIBridge {
public:
    AIBridge();
    ~AIBridge();
    
    bool connect(const juce::String& host = "127.0.0.1", int port = 7891);
    void disconnect();
    bool isConnected() const;
    
    juce::String sendRequest(const juce::var& payload);
    
private:
    std::unique_ptr<juce::StreamingSocket> socket;
    juce::CriticalSection lock;
};
