# Use the latest LTS version of Node.js
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install
RUN npm install react-pdf
RUN npm install node-fetch
RUN npm install react-intersection-observer

# Copy the rest of your application files
COPY . .

# Expose the port your app runs on
EXPOSE 3000

# Start the app in development mode (hot reloading enabled)
CMD ["npm", "run", "dev"]
