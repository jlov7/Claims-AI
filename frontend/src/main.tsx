import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "./styles/joyride-custom.css";
import { ChakraProvider, ColorModeScript } from "@chakra-ui/react";
import theme from "./theme.ts";
import { UploadProvider } from "./context/UploadContext.tsx";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <ColorModeScript initialColorMode="light" />
      <UploadProvider>
        <App />
      </UploadProvider>
    </ChakraProvider>
  </React.StrictMode>,
);
