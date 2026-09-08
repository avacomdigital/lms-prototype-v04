namespace Avacom.Lms.Core.Models;

public sealed record ConnectionOptions(string StudentName, string ServerAddress)
{
    public static readonly ConnectionOptions Default = new("Ethan Martínez", "http://192.168.1.10:8000");

    public Uri ApiBaseUri => Normalize(ServerAddress);

    public Uri WebSocketBaseUri
    {
        get
        {
            var builder = new UriBuilder(ApiBaseUri)
            {
                Scheme = ApiBaseUri.Scheme == Uri.UriSchemeHttps ? "wss" : "ws"
            };
            return builder.Uri;
        }
    }

    public static Uri Normalize(string address)
    {
        var value = address.Trim();
        if (!value.Contains("://", StringComparison.Ordinal))
        {
            value = $"http://{value}";
        }

        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
        {
            throw new ArgumentException("Ingresa una dirección HTTP válida.", nameof(address));
        }

        return uri.AbsoluteUri.EndsWith('/') ? uri : new Uri(uri.AbsoluteUri + "/");
    }
}

