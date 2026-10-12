import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:hmp_client/hmp_client.dart';

Future<void> main(List<String> args) async {
  final config =
      jsonDecode(await File(args.single).readAsString())
          as Map<String, dynamic>;
  final iid = InstanceId.parse(config['iid'] as String);
  final wrong = PinnedConnectionPool(
    connector: createPinnedConnector(),
    pin: InstanceId.parse(List.filled(52, 'a').join()),
    endpoints: [Uri.parse(config['endpoint'] as String)],
  );
  var rejected = false;
  try {
    await wrong.send(
      HttpRequestData(method: 'GET', target: config['path'] as String),
    );
  } on PinMismatch {
    rejected = true;
  } finally {
    await wrong.closeAll();
  }
  if (!rejected) throw StateError('wrong pin was accepted');
  final pool = PinnedConnectionPool(
    connector: createPinnedConnector(),
    pin: iid,
    endpoints: [Uri.parse(config['endpoint'] as String)],
  );
  try {
    final response = await pool.send(
      HttpRequestData(
        method: 'GET',
        target: config['path'] as String,
        headers: {
          'Authorization': 'Bearer ${config['token']}',
          'HMP-Instance': iid.value,
        },
      ),
    );
    if (response.status != 200 ||
        sha256.convert(response.body).toString() != config['sha256']) {
      throw StateError('synthetic image verification failed');
    }
    stdout.writeln(
      jsonEncode({
        'spkiPinnedFetch': true,
        'wrongPinRejected': true,
        'bytes': response.body.length,
      }),
    );
  } finally {
    await pool.closeAll();
  }
}
