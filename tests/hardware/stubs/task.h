#pragma once
using TaskHandle_t = void *;
inline TaskHandle_t xTaskGetCurrentTaskHandle()
{
    static thread_local char task;
    return &task;
}
