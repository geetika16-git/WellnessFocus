using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace WellnessFocus;

public class Program
{
    public static void Main(string[] args)
    {
        if (args.Length > 0)
        {
            if (args[0] == "--install" || args[0] == "-i")
            {
                InstallService();
                return;
            }
            if (args[0] == "--uninstall" || args[0] == "-u")
            {
                UninstallService();
                return;
            }
            if (args[0] == "--console" || args[0] == "-c")
            {
                RunConsole(args);
                return;
            }
        }

        RunService(args);
    }

    private static void RunService(string[] args)
    {
        Host.CreateDefaultBuilder(args)
            .UseWindowsService(options =>
            {
                options.ServiceName = "WellnessFocus";
            })
            .ConfigureServices((context, services) =>
            {
                services.AddHostedService<WellnessService>();
            })
            .ConfigureLogging(logging =>
            {
                logging.AddEventLog();
            })
            .Build()
            .Run();
    }

    private static void RunConsole(string[] args)
    {
        using var host = Host.CreateDefaultBuilder(args)
            .ConfigureServices((context, services) =>
            {
                services.AddHostedService<WellnessService>();
            })
            .Build();

        host.Run();
    }

    private static void InstallService()
    {
        Console.WriteLine("Installing Wellness Focus Service...");
        RunProcess("sc", $"create WellnessFocus binPath=\"{GetExePath()}\" start=auto DisplayName=\"Wellness Focus Service\"");
        RunProcess("sc", "description WellnessFocus \"Enforces wellness breaks, app limits, and website blocking.\"");
        Console.WriteLine("Service installed. Starting...");
        RunProcess("sc", "start WellnessFocus");
        Console.WriteLine("Service started successfully.");
    }

    private static void UninstallService()
    {
        Console.WriteLine("Stopping Wellness Focus Service...");
        RunProcess("sc", "stop WellnessFocus");
        Thread.Sleep(2000);
        Console.WriteLine("Removing service...");
        RunProcess("sc", "delete WellnessFocus");
        Console.WriteLine("Service removed.");
    }

    private static void RunProcess(string fileName, string arguments)
    {
        var process = new System.Diagnostics.Process
        {
            StartInfo = new System.Diagnostics.ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                UseShellExecute = true,
                Verb = "runas",
                WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden
            }
        };
        process.Start();
        process.WaitForExit();
    }

    private static string GetExePath()
    {
        var path = System.Diagnostics.Process.GetCurrentProcess().MainModule?.FileName;
        return path ?? "";
    }
}
