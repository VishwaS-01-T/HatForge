#include "AIBridge.h"

AIBridge::AIBridge() : socket(new juce::StreamingSocket()) {}

AIBridge::~AIBridge() {
    disconnect();
}

bool AIBridge::connect(const juce::String& host, int port) {
    juce::ScopedLock sl(lock);
    if (socket->isConnected()) return true;
    return socket->connect(host, port, 5000);
}

void AIBridge::disconnect() {
    juce::ScopedLock sl(lock);
    socket->close();
}

bool AIBridge::isConnected() const {
    juce::ScopedLock sl(lock);
    return socket->isConnected();
}

juce::String AIBridge::sendRequest(const juce::var& payload) {
    juce::ScopedLock sl(lock);
    
    juce::String errorJson = "{\"status\": \"error\", \"message\": \"Failed to connect\"}";
    
    if (!socket->isConnected()) {
        if (!socket->connect("127.0.0.1", 7891, 5000)) {
            return errorJson;
        }
    }
    
    juce::String jsonStr = juce::JSON::toString(payload);
    juce::MemoryBlock block;
    juce::int32 length = juce::ByteOrder::swapIfLittleEndian((juce::int32)jsonStr.getNumBytesAsUTF8());
    block.append(&length, 4);
    block.append(jsonStr.toRawUTF8(), jsonStr.getNumBytesAsUTF8());
    
    if (socket->write(block.getData(), block.getSize()) != block.getSize()) {
        return "{\"status\": \"error\", \"message\": \"Failed to write to socket\"}";
    }
    
    juce::int32 replyLength = 0;
    if (socket->read(&replyLength, 4, true) == 4) {
        replyLength = juce::ByteOrder::swapIfLittleEndian(replyLength);
        if (replyLength > 0 && replyLength < 10000000) {
            juce::MemoryBlock replyBlock(replyLength, true);
            if (socket->read(replyBlock.getData(), replyLength, true) == replyLength) {
                return juce::String::fromUTF8((const char*)replyBlock.getData(), replyLength);
            }
        }
    }
    
    return "{\"status\": \"error\", \"message\": \"Failed to read from socket\"}";
}
