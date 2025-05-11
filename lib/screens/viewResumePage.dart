import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart'; // Make sure to add this dependency to pubspec.yaml
import 'package:http/http.dart' as http;

// Function to fetch resume from Flask backend
Future<String> fetchResume(int resumeId) async {
  final response =
      await http.get(Uri.parse('http://your-api-url/view_resume/$resumeId'));

  if (response.statusCode == 200) {
    // Return the base64 string from the response
    return response.body;
  } else {
    throw Exception('Failed to load resume');
  }
}

class ViewResumePage extends StatefulWidget {
  final int resumeId;

  // Constructor to accept resume ID for fetching data
  ViewResumePage(
      {required this.resumeId,
      required Uint8List resumeFile,
      required String resumeBase64});

  @override
  _ViewResumePageState createState() => _ViewResumePageState();
}

class _ViewResumePageState extends State<ViewResumePage> {
  late Future<String> _resumeBase64; // Store the future result of base64 resume

  @override
  void initState() {
    super.initState();
    // Fetch the resume data once the page is loaded
    _resumeBase64 = fetchResume(widget.resumeId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('View Resume'),
        backgroundColor: Colors.indigo,
      ),
      body: FutureBuilder<String>(
        future: _resumeBase64, // Await the base64 string response
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            // Show a loading indicator while the resume is being fetched
            return Center(child: CircularProgressIndicator());
          } else if (snapshot.hasError) {
            // Show an error message if something goes wrong
            return Center(child: Text('Error: ${snapshot.error}'));
          } else if (snapshot.hasData) {
            // Successfully fetched the base64 data, now decode it
            Uint8List resumeFile = base64Decode(snapshot.data!);

            return PDFView(
              // Use the byte data to render the PDF
              filePath: '', // Leave empty since we're using byte data
              pdfData: resumeFile, // Provide the decoded resume file data
            );
          } else {
            return Center(child: Text('No data available.'));
          }
        },
      ),
    );
  }
}
