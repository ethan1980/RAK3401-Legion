#pragma once
#include "concurrency/LockGuard.h"
#include "configuration.h"
#include <algorithm>
#include <cstring>
#include <map>
#include <memory>
#include <string>
#include <vector>

using String = std::string;
constexpr int FILE_O_READ = 0;
constexpr int FILE_O_WRITE = 1;

class Print
{
  public:
    virtual ~Print() = default;
    virtual size_t write(uint8_t value) = 0;
    virtual size_t write(const uint8_t *data, size_t size) = 0;
};

class File
{
  public:
    File() = default;
    File(std::shared_ptr<std::vector<uint8_t>> content, bool writable)
        : bytes(std::move(content)), writable(writable), offset(writable ? bytes->size() : 0)
    {
    }
    explicit operator bool() const { return bool(bytes); }
    size_t size() const { return bytes ? bytes->size() : 0; }
    int read() { return bytes && offset < bytes->size() ? (*bytes)[offset++] : -1; }
    int read(uint8_t *out, size_t size)
    {
        size_t copied = 0;
        for (int value; copied < size && (value = read()) >= 0;)
            out[copied++] = static_cast<uint8_t>(value);
        return static_cast<int>(copied);
    }
    size_t write(uint8_t value) { return write(&value, 1); }
    size_t write(const uint8_t *data, size_t size);
    void close();

  private:
    std::shared_ptr<std::vector<uint8_t>> bytes;
    bool writable = false;
    size_t offset = 0;
};

struct FakeFilesystem {
    std::map<std::string, std::shared_ptr<std::vector<uint8_t>>> files;
    bool failRename = false;
    bool corruptClose = false;
    bool appendClose = false;
    bool shortWrites = false;
    size_t mutations = 0;
    std::string failOpenName;
    bool exists(const char *name) const { return std::strcmp(name, "/") == 0 || files.count(name) != 0; }
    void mkdir(const char *) {}
    void _lockFS() {}
    void _unlockFS() {}
    bool remove(const char *name)
    {
        ++mutations;
        return files.erase(name) != 0;
    }
    File open(const char *name, int mode)
    {
        if (name == failOpenName)
            return File();
        if (mode == FILE_O_WRITE && !exists(name))
            files[name] = std::make_shared<std::vector<uint8_t>>();
        const auto it = files.find(name);
        return it == files.end() ? File() : File(it->second, mode == FILE_O_WRITE);
    }
    bool rename(const char *source, const char *dest)
    {
        ++mutations;
        if (failRename || !exists(source))
            return false;
        files[dest] = files[source];
        files.erase(source);
        return true;
    }
    void put(const char *name, const std::vector<uint8_t> &data) { files[name] = std::make_shared<std::vector<uint8_t>>(data); }
    std::vector<uint8_t> get(const char *name) const { return *files.at(name); }
};
extern FakeFilesystem fakeFs;
#define FSCom fakeFs

inline size_t File::write(const uint8_t *data, size_t size)
{
    if (!bytes || !writable)
        return 0;
    if (fakeFs.shortWrites && size)
        --size;
    ++fakeFs.mutations;
    bytes->insert(bytes->end(), data, data + size);
    offset += size;
    return size;
}

inline void File::close()
{
    if (writable && bytes) {
        if (fakeFs.corruptClose && bytes->size() >= 2) {
            (*bytes)[0] ^= 1;
            (*bytes)[1] ^= 1;
            fakeFs.corruptClose = false;
        }
        if (fakeFs.appendClose) {
            bytes->insert(bytes->end(), {0, 0});
            fakeFs.appendClose = false;
        }
    }
    writable = false;
    bytes.reset();
}

inline bool renameFile(const char *source, const char *dest)
{
    return fakeFs.rename(source, dest);
}
