import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { TranscriptInput } from './components/TranscriptInput';
import { SentenceList } from './components/SentenceList';
import { SrtPreview } from './components/SrtPreview';
import { Footer } from './components/Footer';
import { VideoGenerator } from './components/VideoGenerator'; // New component
import { generateImageFromText, generateSpeechFromText } from './services/geminiService';
import { createVideoFromSentences } from './services/videoService'; // New service
import { transcribeAudio } from './services/audioService'; // New audio service
import type { Sentence } from './types';
import { formatSrtTime, estimateTimingsAndSplit } from './utils/srtHelper';

const App: React.FC = () => {
  const [rawTranscript, setRawTranscript] = useState<string>('');
  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [srtContent, setSrtContent] = useState<string>('');
  const [isProcessingTranscript, setIsProcessingTranscript] = useState<boolean>(false);
  const [isAudioProcessing, setIsAudioProcessing] = useState<boolean>(false); // New state for audio processing
  const [fileName, setFileName] = useState<string | null>(null);

  const [isVideoGenerating, setIsVideoGenerating] = useState<boolean>(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [backgroundMusicUrl, setBackgroundMusicUrl] = useState<string | null>(null); // New state for background music

  const handleTranscriptSubmit = useCallback(async () => {
    if (!rawTranscript.trim()) {
      setSentences([]);
      setSrtContent('');
      setVideoUrl(null);
      setVideoError(null);
      return;
    }
    setIsProcessingTranscript(true);
    setVideoUrl(null);
    setVideoError(null);
    
    // Removed simulated processing delay

    const newSentences = estimateTimingsAndSplit(rawTranscript);
    setSentences(newSentences);

    const srtEntries = newSentences.map((sentence, index) => {
      return `${index + 1}\n${formatSrtTime(sentence.startTime)} --> ${formatSrtTime(sentence.endTime)}\n${sentence.text}\n`;
    });
    setSrtContent(srtEntries.join('\n\n'));
    setIsProcessingTranscript(false);
  }, [rawTranscript]);

  const handleGenerateImage = useCallback(async (sentenceId: string) => {
    setSentences(prevSentences =>
      prevSentences.map(s =>
        s.id === sentenceId ? { ...s, imageLoading: true, imageError: undefined, imageUrl: undefined } : s
      )
    );
    setVideoUrl(null); // Invalidate previous video if images change

    const sentenceToProcess = sentences.find(s => s.id === sentenceId);
    if (!sentenceToProcess) return;

    try {
      // API Key is now handled within geminiService.ts
      const imageUrl = await generateImageFromText(sentenceToProcess.text);
      setSentences(prevSentences =>
        prevSentences.map(s =>
          s.id === sentenceId ? { ...s, imageUrl, imageLoading: false } : s
        )
      );
    } catch (error) {
      console.error("Error generating image:", error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate image.';
      setSentences(prevSentences =>
        prevSentences.map(s =>
          s.id === sentenceId ? { ...s, imageLoading: false, imageError: errorMessage } : s
        )
      );
    }
  }, [sentences]);

  const handleGenerateAudio = useCallback(async (sentenceId: string) => {
    setSentences(prevSentences =>
      prevSentences.map(s =>
        s.id === sentenceId ? { ...s, audioLoading: true, audioError: undefined, audioUrl: undefined } : s
      )
    );
    // Optional: Invalidate video if audio changes and video includes audio in future
    // setVideoUrl(null); 

    const sentenceToProcess = sentences.find(s => s.id === sentenceId);
    if (!sentenceToProcess) return;

    try {
      // API Key is now handled within geminiService.ts
      const audioUrl = await generateSpeechFromText(sentenceToProcess.text);
      setSentences(prevSentences =>
        prevSentences.map(s =>
          s.id === sentenceId ? { ...s, audioUrl, audioLoading: false } : s
        )
      );
    } catch (error) {
      console.error("Error generating audio:", error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate audio.';
      setSentences(prevSentences =>
        prevSentences.map(s =>
          s.id === sentenceId ? { ...s, audioLoading: false, audioError: errorMessage } : s
        )
      );
    }
  }, [sentences]);


  const handleFileSelected = useCallback(async (selectedFile: File | null) => {
    if (selectedFile) {
      setFileName(selectedFile.name);
      setRawTranscript(''); // Clear transcript when new file is selected
      setSentences([]);
      setSrtContent('');
      setVideoUrl(null);
      setVideoError(null);
      setIsAudioProcessing(true); // Start audio processing
      try {
        const transcribedText = await transcribeAudio(selectedFile);
        setRawTranscript(transcribedText);
        // After transcription, automatically trigger transcript submission
        // This will then call estimateTimingsAndSplit and generate SRT
        handleTranscriptSubmit();
      } catch (error) {
        console.error("Error processing audio:", error);
        // Handle error, e.g., show a message to the user
      } finally {
        setIsAudioProcessing(false); // End audio processing
      }
    } else {
      setFileName(null);
    }
  }, []);

  const handleGenerateVideo = useCallback(async () => {
    if (sentences.length === 0) {
      setVideoError("No sentences available to generate video.");
      return;
    }
    setIsVideoGenerating(true);
    setVideoError(null);
    setVideoUrl(null);

    try {
      const generatedVideoUrl = await createVideoFromSentences(sentences, backgroundMusicUrl); // Pass background music URL
      setVideoUrl(generatedVideoUrl);
    } catch (error) {
      console.error("Error generating video:", error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate video.';
      setVideoError(errorMessage);
    } finally {
      setIsVideoGenerating(false);
    }
  }, [sentences]);


  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 text-slate-100">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-8 space-y-8">
        <TranscriptInput
          transcript={rawTranscript}
          onTranscriptChange={setRawTranscript}
          onSubmit={handleTranscriptSubmit}
          isProcessing={isProcessingTranscript || isAudioProcessing} // Pass audio processing state
          onFileSelected={handleFileSelected}
          fileName={fileName}
          isAudioProcessing={isAudioProcessing} // Pass the new prop
        />
        
        {(isProcessingTranscript || isAudioProcessing) && ( // Show spinner for either process
          <div className="flex justify-center items-center p-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400"></div>
            <p className="ml-3 text-lg text-indigo-300">
              {isAudioProcessing ? "Processing audio..." : "Analyzing transcript..."}
            </p>
          </div>
        )}

        {sentences.length > 0 && !isProcessingTranscript && (
          <div className="space-y-8">
            <SrtPreview srtContent={srtContent} />
            <SentenceList 
              sentences={sentences} 
              onGenerateImage={handleGenerateImage}
              onGenerateAudio={handleGenerateAudio} 
            />
            <VideoGenerator
              onGenerateVideo={handleGenerateVideo}
              isGenerating={isVideoGenerating}
              videoUrl={videoUrl}
              error={videoError}
              hasSentences={sentences.length > 0}
              onBackgroundMusicUrlChange={setBackgroundMusicUrl} // Pass setter for background music
              backgroundMusicUrl={backgroundMusicUrl} // Pass background music URL
            />
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
};

export default App;