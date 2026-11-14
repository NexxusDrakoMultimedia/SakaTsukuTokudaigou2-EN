-- Interactive bridge: polls build/emu/cmd.lua every 20 vblanks and executes it inside Flycast.
-- Helper globals available to cmd.lua: dump(addr,size,file), poke(addr,string), peek(addr,n), say(msg), frame()
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
local n = 0
local function log(msg) local f = io.open(OUT .. "live.log", "a"); if f then f:write(n, ": ", tostring(msg), "\n"); f:close() end end
function say(m) log(m) end
function frame() return n end
function peek(addr, len)
  local t = {}
  for i = 0, len - 1 do t[#t + 1] = string.char(flycast.memory.read8(addr + i)) end
  return table.concat(t)
end
function poke(addr, s) for i = 1, #s do flycast.memory.write8(addr + i - 1, s:byte(i)) end log("poked " .. #s .. " bytes @" .. string.format("%x", addr)) end
function dump(addr, size, file)
  local f = io.open(OUT .. file, "wb")
  local pos = 0
  while pos < size do
    local parts = {}
    local last = math.min(pos + 262144, size)
    for a = pos, last - 4, 4 do parts[#parts + 1] = string.pack("<I4", flycast.memory.read32(addr + a)) end
    f:write(table.concat(parts)); pos = last
  end
  f:close(); log("dumped " .. size .. " bytes to " .. file)
end
log("live bridge loaded")
flycast_callbacks = flycast_callbacks or {}
flycast_callbacks.vblank = function()
  n = n + 1
  if n % 20 ~= 0 then return end
  local f = io.open(OUT .. "cmd.lua", "r")
  if not f then return end
  local src = f:read("a"); f:close(); os.remove(OUT .. "cmd.lua")
  local fn, err = load(src, "cmd", "t", _ENV)
  if not fn then log("compile error: " .. tostring(err)); return end
  local ok, e = pcall(fn)
  log("cmd " .. (ok and "ok" or ("ERROR " .. tostring(e))))
end
