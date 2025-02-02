import './globals.css'; 
import React from 'react';
import { AppProps } from 'next/app';

// Define the MyApp component with types
function MyApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}



export default MyApp;

