#include "AIBridge.h"

AIBridge::AIBridge()
    : socket (std::make_unique<juce::StreamingSocket>())
{
}

AIBridge::~AIBridge()
{
    disconnect();
}

bool AIBridge::connect (const juce::String& host, int port)
{
    juce::ScopedLock sl (lock);

    // Always start with a fresh socket to avoid stale-connection issues.
    socket = std::make_unique<juce::StreamingSocket>();
    return socket->connect (host, port, 5000);
}

void AIBridge::disconnect()
{
    juce::ScopedLock sl (lock);
    if (socket != nullptr)
        socket->close();
}

bool AIBridge::isConnected() const
{
    juce::ScopedLock sl (lock);
    return socket != nullptr && socket->isConnected();
}

juce::String AIBridge::sendRequest (const juce::var& payload)
{
    juce::ScopedLock sl (lock);

    const juce::String errorJson =
        "{\"status\": \"error\", \"message\": \"Bridge communication failed\"}";

    if (socket == nullptr || ! socket->isConnected())
    {
        // Try a fresh connection
        socket = std::make_unique<juce::StreamingSocket>();
        if (! socket->connect ("127.0.0.1", 7891, 5000))
            return errorJson;
    }

    // ── Serialize payload to JSON UTF-8 bytes ──
    juce::String jsonStr = juce::JSON::toString (payload);
    auto utf8 = jsonStr.toUTF8();
    int numBytes = (int) utf8.sizeInBytes() - 1; // exclude null-terminator

    // ── Send: 4-byte Big-Endian length header + JSON body ──
    juce::uint32 lengthBE = juce::ByteOrder::swapIfLittleEndian ((juce::uint32) numBytes);
    if (socket->write (&lengthBE, 4) != 4)
    {
        disconnect();
        return errorJson;
    }
    if (socket->write (utf8.getAddress(), numBytes) != numBytes)
    {
        disconnect();
        return errorJson;
    }

    // ── Receive: 4-byte Big-Endian length header ──
    juce::uint32 replyLenBE = 0;
    if (socket->read (&replyLenBE, 4, true) != 4)
    {
        disconnect();
        return errorJson;
    }
    juce::uint32 replyLen = juce::ByteOrder::swapIfLittleEndian (replyLenBE);

    if (replyLen == 0 || replyLen > 10000000) // sanity check ~10 MB
    {
        disconnect();
        return errorJson;
    }

    // ── Receive: JSON body ──
    juce::MemoryBlock replyBlock ((size_t) replyLen, true);
    if (socket->read (replyBlock.getData(), (int) replyLen, true) != (int) replyLen)
    {
        disconnect();
        return errorJson;
    }

    // Close after a successful round-trip (one-shot connection model).
    disconnect();

    return juce::String::fromUTF8 ((const char*) replyBlock.getData(), (int) replyLen);
}
