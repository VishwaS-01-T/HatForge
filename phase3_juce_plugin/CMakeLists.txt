cmake_minimum_required(VERSION 3.22)
project(HatForge VERSION 1.0.0)

# Assume JUCE is located in vendor/JUCE relative to the plugin folder
add_subdirectory(vendor/JUCE)

juce_add_plugin(HatForge
    PLUGIN_MANUFACTURER_CODE Htfg
    PLUGIN_CODE Hfg1
    FORMATS VST3 Standalone
    PRODUCT_NAME "HatForge"
    COMPANY_NAME "HatForge Audio"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT TRUE
    PLUGIN_CATEGORY kPlugCategEffect
)

target_sources(HatForge PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginProcessor.h
    Source/PluginEditor.cpp
    Source/PluginEditor.h
    Source/MidiGenerator.cpp
    Source/MidiGenerator.h
    Source/AIBridge.cpp
    Source/AIBridge.h
)

target_compile_definitions(HatForge PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

target_link_libraries(HatForge PRIVATE
    juce::juce_audio_utils
    juce::juce_audio_plugin_client
    juce::juce_core
    juce::juce_events
    juce::juce_data_structures
)
