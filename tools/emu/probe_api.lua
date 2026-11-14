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
local OUT = ROOT .. "build/emu/api.txt"
local function keys(t) local r = {} if type(t) == "table" then for k, v in pairs(t) do r[#r+1] = tostring(k) .. ":" .. type(v) end end table.sort(r) return table.concat(r, ", ") end
local f = io.open(OUT, "w")
for _, n in ipairs({ "config", "emulator", "input", "memory", "state", "ui" }) do f:write(n, " = ", keys(flycast[n]), "\n") end
f:close()
