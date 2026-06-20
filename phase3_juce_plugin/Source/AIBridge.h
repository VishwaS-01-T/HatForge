#pragma once

#include <JuceHeader.h>

/**
 * AIBridge — TCP client that talks to the HatForge Python server.
 *
 * The bridge creates a fresh TCP connection for each request (connect → send →
 * recv → close). This avoids stale-socket bugs and is perfectly fine for the
 * low-frequency nature of hat-generation requests.
 *
 * Thread-safety: sendRequest() is guarded by an internal CriticalSection so it
 * can be called from any single background thread without external locking.
 * It must NEVER be called from the audio thread.
 */
class AIBridge
{
public:
    AIBridge();
    ~AIBridge();

    /** Attempt a connection to the Python server.
     *  Returns true if the connection succeeds.
     *  The connection is stored for the subsequent sendRequest() call. */
    bool connect (const juce::String& host = "127.0.0.1", int port = 7891);

    /** Close the current connection, if any. */
    void disconnect();

    /** Returns true if a socket is currently connected. */
    bool isConnected() const;

    /** Send a JSON payload over the length-prefixed protocol and return the
     *  server's JSON response as a juce::String.
     *  On failure returns a JSON string with status "error". */
    juce::String sendRequest (const juce::var& payload);

private:
    std::unique_ptr<juce::StreamingSocket> socket;
    juce::CriticalSection lock;
};
