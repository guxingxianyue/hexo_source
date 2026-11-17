import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

public class GemmaLocalDemo {
    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2) {
            throw new IllegalArgumentException(
                    "Usage: java GemmaLocalDemo.java request.json [http://127.0.0.1:11434]");
        }
        URI base = URI.create(args.length == 2 ? args[1] : "http://127.0.0.1:11434");
        if (!"http".equals(base.getScheme())
                || !("127.0.0.1".equals(base.getHost()) || "localhost".equals(base.getHost()))
                || base.getRawUserInfo() != null || base.getQuery() != null
                || base.getFragment() != null
                || !(base.getPath().isEmpty() || "/".equals(base.getPath()))) {
            throw new IllegalArgumentException("Use an HTTP loopback base URL");
        }
        String body = Files.readString(Path.of(args[0]), StandardCharsets.UTF_8);
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        HttpRequest request = HttpRequest.newBuilder(base.resolve("/api/chat"))
                .timeout(Duration.ofSeconds(120))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                .build();
        HttpResponse<String> response = client.send(request,
                HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() / 100 != 2) {
            throw new IllegalStateException(
                    "Ollama HTTP " + response.statusCode() + ": " + response.body());
        }
        System.out.println(response.body());
    }
}
