-- Flycast scenario harness. Scenario file path is taken from tools/emu/scenario.lua (written per run).
-- scenario = { press = { {frame=, buttons=, hold=}, ... }, dump = { {frame=, addr=, size=, file=}, ... }, exit_at = N }
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
local scenario = dofile(ROOT .. "tools/emu/scenario.lua")
local frame, releases = 0, {}
local function status(msg) local f = io.open(OUT .. "status.txt", "a"); if f then f:write(frame, ": ", msg, "\n"); f:close() end end
status("harness loaded")
flycast_callbacks = flycast_callbacks or {}
flycast_callbacks.vblank = function()
  frame = frame + 1
  for _, p in ipairs(scenario.press or {}) do
    if frame == p.frame then
      local ok, err = pcall(flycast.input.pressButtons, p.port or 1, p.buttons)
      status("press " .. tostring(p.buttons) .. " ok=" .. tostring(ok) .. " err=" .. tostring(err))
      if not ok then
        for _, v in ipairs({ p.buttons, tostring(p.buttons) }) do
          local ok2, err2 = pcall(flycast.input.pressButtons, v)
          status("  try pressButtons(" .. tostring(v) .. ") ok=" .. tostring(ok2) .. " err=" .. tostring(err2))
        end
      end
      local okb, bt = pcall(flycast.input.getButtons, p.port or 1)
      status("  getButtons ok=" .. tostring(okb) .. " v=" .. tostring(bt))
      releases[#releases + 1] = { at = frame + (p.hold or 4), port = p.port or 1, b = p.buttons }
    end
  end
  for i = #releases, 1, -1 do
    local r = releases[i]
    if frame >= r.at then local okr, er = pcall(flycast.input.releaseButtons, r.port, r.b); status("release " .. r.b .. " ok=" .. tostring(okr) .. " " .. tostring(er)); table.remove(releases, i) end
  end
  for _, d in ipairs(scenario.dump or {}) do
    if frame == d.frame then
      local t = flycast.memory.readTable8(d.addr, d.size)
      local parts = {}
      for i = 1, #t, 4096 do parts[#parts + 1] = string.char(table.unpack(t, i, math.min(i + 4095, #t))) end
      local f = io.open(OUT .. d.file, "wb"); f:write(table.concat(parts)); f:close(); status("dumped " .. d.file)
    end
  end
  for _, w in ipairs(scenario.write or {}) do
    if frame == w.frame then
      for i = 1, #w.bytes do flycast.memory.write8(w.addr + i - 1, w.bytes:byte(i)) end
      status("wrote " .. #w.bytes .. " bytes at " .. string.format("%x", w.addr))
    end
  end
  if scenario.exit_at and frame == scenario.exit_at then status("exit"); flycast.emulator.exit() end
end
