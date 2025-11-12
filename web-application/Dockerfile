# Use official lightweight nginx image
FROM nginx:alpine

# Copy your single index.html into nginx's default web root
COPY index.html /usr/share/nginx/html/

# Optional: remove default nginx welcome page (just in case)
RUN rm -f /usr/share/nginx/html/index.html

# Expose port 7777 *inside* the container (nginx will still serve on 80 internally)
# We'll map 7777 → 80 at runtime
EXPOSE 80

# Keep default nginx ENTRYPOINT — no need to override