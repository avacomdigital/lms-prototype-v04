using Avacom.Lms.Core.Models;
namespace Avacom.Lms.Core.Tests;
public sealed class ConnectionOptionsTests
{
    [Theory]
    [InlineData("192.168.1.10:8000", "http://192.168.1.10:8000/")]
    [InlineData("http://127.0.0.1:8000", "http://127.0.0.1:8000/")]
    [InlineData("https://ops.local:8000/", "https://ops.local:8000/")]
    public void Normalize_ReturnsAbsoluteApiAddress(string input, string expected) => Assert.Equal(expected, ConnectionOptions.Normalize(input).AbsoluteUri);

    [Fact]
    public void WebSocketBaseUri_UsesMatchingSecureScheme()
    {
        var options = new ConnectionOptions("Ethan", "https://ops.local:8000");
        Assert.Equal("wss://ops.local:8000/", options.WebSocketBaseUri.AbsoluteUri);
    }

    [Fact]
    public void Normalize_RejectsUnsupportedScheme() => Assert.Throws<ArgumentException>(() => ConnectionOptions.Normalize("ftp://ops.local"));
}
