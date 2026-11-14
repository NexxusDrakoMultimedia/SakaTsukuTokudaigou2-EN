-- Flycast Lua hook: dump Dreamcast main RAM (0x8C000000, 16 MB) to disk at chosen vblank counts.
-- Launch: flycast.exe -config config:LuaFileName=<this file> <disc>
-- Repository root: the SAKATSUKU_ROOT environment variable (tools/emu/launch.ps1 sets it), else the folder this script was
-- loaded from (two levels above tools/emu/), so the repository can live anywhere.
local ROOT = os.getenv("SAKATSUKU_ROOT")
if ROOT == "" then ROOT = nil end
if not ROOT then
  local ok, src = pcall(function() return debug.getinfo(1, "S").source end)
  if ok and type(src) == "string" then ROOT = src:match("^@(.*)tools[/\\]emu[/\\][^/\\]*$") end
end
assert(ROOT, "set SAKATSUKU_ROOT to the repository root (tools/emu/launch.ps1 does this)")
ROOT = ROOT:gsub("\\", "/")
if ROOT == "" then ROOT = "./" elseif ROOT:sub(-1) ~= "/" then ROOT = ROOT .. "/" end
local OUT = ROOT .. "build/emu/"
local DUMP_AT = { 2400, 5400 }          -- vblank numbers (60/s) at which a dump starts
local CHUNK = 65536                     -- 32-bit words per vblank, keeps the emulator responsive
local BASE, SIZE = 0x8C000000, 0x01000000
local frame, job = 0, nil

local function status(msg)
  local f = io.open(OUT .. "status.txt", "a")
  if f then f:write(msg, "\n"); f:close() end
end

status("lua loaded")
status("types: flycast=" .. type(flycast) .. " callbacks=" .. type(flycast_callbacks) .. " memory=" .. type(flycast and flycast.memory))
local function keys(t) local r = {} if type(t) == "table" then for k in pairs(t) do r[#r+1] = tostring(k) end end table.sort(r) return table.concat(r, ",") end
status("flycast keys: " .. keys(flycast)); status("callback keys: " .. keys(flycast_callbacks))
if type(flycast_callbacks) ~= "table" then flycast_callbacks = {} end
flycast_callbacks.vblank = function()
  frame = frame + 1
  if frame == 1 then
    local ok, v = pcall(flycast.memory.read32, BASE + 0x10000)
    status("first vblank; read32(0x8c010000) ok=" .. tostring(ok) .. " v=" .. tostring(v))
  end
  if not job then
    for _, n in ipairs(DUMP_AT) do
      if frame == n then
        job = { f = io.open(OUT .. string.format("ram_%d.bin", n), "wb"), pos = 0, n = n }
        status("dump start at frame " .. n)
      end
    end
  end
  if job then
    local parts = {}
    local last = math.min(job.pos + CHUNK * 4, SIZE)
    for a = job.pos, last - 4, 4 do
      parts[#parts + 1] = string.pack("<I4", flycast.memory.read32(BASE + a))
    end
    job.f:write(table.concat(parts))
    job.pos = last
    if job.pos >= SIZE then
      job.f:close(); status("dump done frame " .. job.n); job = nil
    end
  end
end
