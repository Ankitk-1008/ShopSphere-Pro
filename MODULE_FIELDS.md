# Module field reference

## 1. Authentication and Authorization
Resource: `auth`

Fields: email,password_hash,role,is_active

## 2. User Management
Resource: `users`

Fields: email,full_name,role,is_active

## 3. Customer Registration
Resource: `customer_registrations`

Fields: user_id,phone,email_verified,registration_status

## 4. Customer Profile Management
Resource: `customer_profiles`

Fields: user_id,first_name,last_name,phone,date_of_birth

## 5. Address Management
Resource: `addresses`

Fields: user_id,address_type,line1,line2,city,state,postal_code,country,is_default

## 6. Product Category Management
Resource: `categories`

Fields: name,slug,parent_id,description,is_active

## 7. Brand Management
Resource: `brands`

Fields: name,description,website,is_active

## 8. Product Management
Resource: `products`

Fields: name,description,sku,category_id,brand_id,base_price,is_active

## 9. Product Variants
Resource: `product_variants`

Fields: product_id,sku,size,color,price,stock,is_active

## 10. Product Images and Documents
Resource: `product_media`

Fields: product_id,variant_id,file_name,file_path,mime_type,file_size
