FROM node:22-alpine AS build

WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM node:22-alpine
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/dist ./dist
EXPOSE 3004
CMD ["serve", "-s", "dist", "-l", "3004"]
