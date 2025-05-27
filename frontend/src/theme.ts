import { extendTheme, ThemeConfig } from "@chakra-ui/react";

// Define custom theme configuration
const config: ThemeConfig = {
  initialColorMode: "light",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  colors: {
    brand: {
      50: "#e3f2ff",
      100: "#b3d4ff",
      200: "#81b6ff",
      300: "#4e98ff",
      400: "#1b7aff",
      500: "#0061e6", // brand primary
      600: "#004bb4",
      700: "#003582",
      800: "#001f51",
      900: "#000721",
    },
  },
  fonts: {
    heading: "Inter, system-ui, sans-serif",
    body: "Inter, system-ui, sans-serif",
  },
  fontSizes: {
    xs: "0.75rem",
    sm: "0.875rem",
    md: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
    "3xl": "1.875rem",
    "4xl": "2.25rem",
    "5xl": "3rem",
  },
  space: {
    px: "1px",
    0: "0",
    1: "0.25rem",
    2: "0.5rem",
    3: "0.75rem",
    4: "1rem",
    5: "1.25rem",
    6: "1.5rem",
    8: "2rem",
    10: "2.5rem",
    12: "3rem",
    16: "4rem",
    20: "5rem",
    24: "6rem",
    32: "8rem",
    40: "10rem",
    48: "12rem",
    56: "14rem",
    64: "16rem",
  },
  // Add component-specific default styling
  components: {
    Button: {
      baseStyle: {
        fontWeight: "semibold",
        borderRadius: "md",
      },
      defaultProps: {
        colorScheme: "brand",
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderRadius: "lg",
          boxShadow: "md",
          overflow: "hidden",
        },
        header: {
          py: 4,
          px: 6,
        },
        body: {
          py: 4,
          px: 6,
        },
        footer: {
          py: 4,
          px: 6,
        },
      },
    },
    Heading: {
      baseStyle: {
        fontWeight: "bold",
        color: "gray.800",
      },
    },
    Container: {
      baseStyle: {
        maxW: "container.xl",
        px: { base: 4, md: 6 },
        py: { base: 4, md: 6 },
      },
    },
    Box: {
      baseStyle: {
        borderRadius: "md",
      },
    },
  },
  styles: {
    global: {
      // Global styles applied to the whole app
      body: {
        bg: "gray.50",
        color: "gray.800",
      },
    },
  },
});

export default theme;
