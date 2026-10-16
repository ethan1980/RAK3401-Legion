#pragma once
#include "mesh/LegionRecoveryPolicy.h"
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
