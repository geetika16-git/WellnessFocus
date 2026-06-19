using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace WellnessFocus;

public class WellnessService : BackgroundService
{
    private readonly ILogger<WellnessService> _logger;
    private readonly string _appDataDir;
    private readonly string _configPath;
    private readonly string _dbPath;
    private Timer? _watchdogTimer;
    private Timer? _blockingTimer;
    private JsonDocument? _config;

    public WellnessService(ILogger<WellnessService> logger)
    {
        _logger = logger;
        _appDataDir = Path.Combine(
            Environment.GetEnvironmentVariable("ProgramData") ?? "C:\\ProgramData",
            "WellnessFocus"
        );
        _configPath = Path.Combine(_appDataDir, "config.json");
        _dbPath = Path.Combine(_appDataDir, "activity.db");
        Directory.CreateDirectory(_appDataDir);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Wellness Focus Service starting");

        _watchdogTimer = new Timer(WatchdogCheck, null, TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(10));
        _blockingTimer = new Timer(EnforceBlocks, null, TimeSpan.FromSeconds(15), TimeSpan.FromSeconds(15));

        try
        {
            await Task.Delay(Timeout.Infinite, stoppingToken);
        }
        catch (TaskCanceledException)
        {
            _logger.LogInformation("Wellness Focus Service stopping");
        }
        finally
        {
            _watchdogTimer?.Dispose();
            _blockingTimer?.Dispose();
        }
    }

    private void WatchdogCheck(object? state)
    {
        var running = Process.GetProcessesByName("WellnessFocusUI");
        if (running.Length == 0)
        {
            _logger.LogWarning("UI Client is not running (launched via startup folder)");
        }
    }

    private void EnforceBlocks(object? state)
    {
        try
        {
            _config = LoadConfig();
            if (_config == null) return;

            var blockedApps = GetBlockedAppsList();
            if (blockedApps.Count > 0)
            {
                KillBlockedProcesses(blockedApps);
            }

            var blockedWebsites = GetBlockedWebsitesList();
            if (blockedWebsites.Count > 0)
            {
                UpdateHostsFile(blockedWebsites);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error enforcing blocks");
        }
    }

    private JsonDocument? LoadConfig()
    {
        try
        {
            if (!File.Exists(_configPath))
                return null;
            var json = File.ReadAllText(_configPath, Encoding.UTF8);
            return JsonDocument.Parse(json);
        }
        catch
        {
            return null;
        }
    }

    private List<string> GetBlockedAppsList()
    {
        var apps = new List<string>();
        if (_config == null) return apps;

        if (_config.RootElement.TryGetProperty("app_schedule", out var schedule))
        {
            foreach (var app in schedule.EnumerateObject())
            {
                apps.Add(app.Name.ToLower());
            }
        }

        return apps;
    }

    private void KillBlockedProcesses(List<string> blockedApps)
    {
        foreach (var process in Process.GetProcesses())
        {
            try
            {
                var name = process.ProcessName.ToLower() + ".exe";
                if (blockedApps.Contains(name) && IsProcessRunningOnDisallowedDay(name))
                {
                    process.Kill();
                    _logger.LogInformation("Killed blocked process: {Process}", process.ProcessName);
                }
            }
            catch
            {
                // Skip processes we can't access
            }
        }
    }

    private bool IsProcessRunningOnDisallowedDay(string processName)
    {
        if (_config == null) return false;

        if (!_config.RootElement.TryGetProperty("app_schedule", out var schedule))
            return false;

        if (!schedule.TryGetProperty(
            processName.Replace(".exe", ""),
            out var appEntry))
            return false;

        var today = DateTime.Now.ToString("ddd");
        if (appEntry.TryGetProperty("allowed_days", out var days))
        {
            foreach (var day in days.EnumerateArray())
            {
                if (day.GetString() == today)
                    return false;
            }
            return true;
        }

        if (appEntry.TryGetProperty("max_minutes", out var maxMin))
        {
            var todayMinutes = GetTodayAppMinutes(processName);
            return todayMinutes >= maxMin.GetInt32();
        }

        return false;
    }

    private int GetTodayAppMinutes(string processName)
    {
        try
        {
            using var conn = new System.Data.SQLite.SQLiteConnection($"Data Source={_dbPath}");
            conn.Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT COALESCE(SUM(duration_seconds), 0) / 60.0
                FROM app_usage_log
                WHERE process_name = @name
                  AND date(start_time, 'localtime') = date('now', 'localtime')";
            cmd.Parameters.AddWithValue("@name", processName);
            var result = cmd.ExecuteScalar();
            return Convert.ToInt32(result);
        }
        catch
        {
            return 0;
        }
    }

    private List<string> GetBlockedWebsitesList()
    {
        var sites = new List<string>();
        if (_config == null) return sites;

        if (_config.RootElement.TryGetProperty("blocked_websites", out var websites))
        {
            foreach (var site in websites.EnumerateArray())
            {
                sites.Add(site.GetString() ?? "");
            }
        }

        return sites;
    }

    private void UpdateHostsFile(List<string> blockedWebsites)
    {
        try
        {
            var hostsPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                "drivers", "etc", "hosts"
            );

            var lines = File.ReadAllLines(hostsPath).ToList();
            var startMarker = "# BEGIN WellnessFocus Block";
            var endMarker = "# END WellnessFocus Block";
            var startIdx = lines.FindIndex(l => l.Trim() == startMarker);
            var endIdx = lines.FindIndex(l => l.Trim() == endMarker);

            if (startIdx >= 0 && endIdx >= 0)
            {
                lines.RemoveRange(startIdx, endIdx - startIdx + 1);
            }

            if (blockedWebsites.Count > 0)
            {
                lines.Add(startMarker);
                foreach (var site in blockedWebsites)
                {
                    lines.Add($"127.0.0.1 {site}");
                    lines.Add($"::1 {site}");
                }
                lines.Add(endMarker);
            }

            File.WriteAllLines(hostsPath, lines);
        }
        catch (UnauthorizedAccessException)
        {
            _logger.LogWarning("Cannot modify hosts file - insufficient privileges");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating hosts file");
        }
    }
}
