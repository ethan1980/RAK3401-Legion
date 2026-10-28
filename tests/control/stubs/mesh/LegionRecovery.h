#pragma once
#include "mesh/LegionRecoveryPolicy.h"
#include "mesh/LegionBackupStatus.h"
#include "configuration.h"
#include <cstdio>
extern unsigned backupOperations;
extern LegionBackupCommand lastBackup;
inline void legionRecoveryCommand(LegionBackupCommand command, char *reply, size_t size)
{
    ++backupOperations;
    lastBackup = command;
    std::snprintf(reply, size, "Backup !abcdef01: simulated durable result");
}
inline bool legionRecoveryNotice(char *, size_t, uint8_t) { return false; }
inline bool legionRecoveryNoticeAttempt() { return false; }
inline void legionRecoveryNoticeQueued() {}
extern bool recoveryBlocked;
inline bool legionRecoveryIsBlocked() { return recoveryBlocked; }
inline unsigned channelSaveCalls = 0, backupStatusReads = 0;
inline LegionChannelSave channelSaveResult = LegionChannelSave::Saved;
inline meshtastic_Channel persistedChannel{};
inline LegionBackupStatus simulatedBackupStatus{};
inline LegionChannelSave legionSaveChannel(const meshtastic_Channel &channel)
{
    ++channelSaveCalls;
    if (channelSaveResult == LegionChannelSave::Saved)
        persistedChannel = channel;
    return channelSaveResult;
}
inline LegionBackupStatus legionBackupStatus()
{
    ++backupStatusReads;
    return simulatedBackupStatus;
}
