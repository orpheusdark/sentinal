# Troubleshooting

| Symptom | Check and recovery |
|---|---|
| Dashboard not opening | Confirm launcher is running, use Open dashboard, check port and data-directory logs; another app may own port 5000 |
| Camera unavailable | Close other camera apps, verify drivers and OS camera permission manually; dashboard stays accessible and discovery retries |
| Frozen app missing resources | Extract the complete portable archive including _internal; do not copy only Sentinel.exe |
| Settings do not apply | Restart after saving; environment overrides take precedence; inspect selected user config |
| Invalid JSON/startup fails | Restore valid JSON from backup/example; comments and triple-quoted headers are not JSON |
| Network bind rejected | Enable authentication and configure a private password before binding a non-loopback interface |
| 401 API response | Log in or provide X-API-Key according to your configured auth mode; keys in URLs are unsupported |
| 403 settings response | Send the custom write header and JSON content type; use the same origin as the dashboard |
| HTTPS failure | Supply both certificate/key paths and a valid trusted chain; certificate validation is enforced |
| Archive row downloads 404 | Retention may have removed the video; metadata can outlive files; restore video from backup if needed |
| Video does not play in browser | Download and open in a compatible player; mp4v is not guaranteed to have browser codec support |
| High CPU/bandwidth | Reduce camera FPS/resolution, preview refresh, or pause preview; hidden-tab polling pauses |
| Telegram delayed/missing | Check enabled flag and private token/chat ID; send requires Internet; network failures can delay capture |
| App cannot install/update | Close the existing process; ensure your local Programs/data directories are writable and enough disk space exists |
| Test/build temp rename denied | Use a writable temporary directory; pytest --basetemp=./build/test-temp; build --sdist-extract-dir ./build/sdist-temp |

Logs are JSON under the active data directory's logs/. Share only redacted excerpts. Before changing a database, make a backup; do not delete the only database to troubleshoot. If startup cannot create schema, verify database file permissions and disk space, then test a separate empty data directory. An abrupt process kill can leave an incomplete MP4; graceful Stop is preferred.
